import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from backend.models.document import DocumentResponse, DocumentUploadResponse, DocumentCategoryUpdate
from backend.routes.auth import get_current_user, require_admin
from backend.services.document_parser import compute_sha256, extract_text_from_bytes, chunk_text
from backend.services.vector_store import FAISSManager
from backend.services.llm_service import GeminiService
from backend.database import get_db

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# Lazy-initialized singletons for vector store and Gemini service
_vector_store: Optional[FAISSManager] = None
_llm_service: Optional[GeminiService] = None


def get_vector_store() -> FAISSManager:
    global _vector_store
    if _vector_store is None:
        _vector_store = FAISSManager()
    return _vector_store


def get_llm_service() -> GeminiService:
    global _llm_service
    if _llm_service is None:
        _llm_service = GeminiService()
    return _llm_service


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("General"),
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Ingests and embeds a document (.txt, .md, .pdf, .docx).
    Uses SHA-256 hashing for cache detection: if unchanged, skips re-embedding.
    Requires Admin privileges.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )

    file_name = file.filename or "uploaded_document"
    file_ext = Path(file_name).suffix.lower()
    file_hash = compute_sha256(file_bytes)

    # 1. Check for SHA-256 cache match
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, file_name FROM documents WHERE file_hash = ?", (file_hash,))
        cached_doc = cursor.fetchone()

    if cached_doc:
        # File unchanged -> 100% cache hit
        return DocumentUploadResponse(
            message="File unchanged. Embedding skipped.",
            chunks_created=0,
            cache_hit=True
        )

    # 2. Extract text from bytes based on file format
    try:
        raw_text = extract_text_from_bytes(file_bytes, file_ext)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract readable text from document"
        )

    # 3. Chunk text (~500 tokens with 50-token overlap)
    chunks = chunk_text(raw_text)
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document resulted in zero chunks"
        )

    # 4. Generate embeddings via Gemini embedding model
    llm = get_llm_service()
    try:
        embeddings = llm.generate_embeddings(chunks)
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Google Gemini API Quota Exceeded (429): Embedding rate limit reached during document ingestion. Please wait a moment or use another API key."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate document embeddings: {err_str}"
        )

    # 5. Add embeddings to FAISS vector index
    vstore = get_vector_store()
    vector_ids = vstore.add_vectors(embeddings)

    # 6. Persist document and chunk metadata in SQLite
    with get_db() as conn:
        cursor = conn.cursor()

        # If a document with the same file_name exists (e.g. updated version), remove old chunks first
        cursor.execute("SELECT id FROM documents WHERE file_name = ?", (file_name,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("DELETE FROM documents WHERE id = ?", (existing["id"],))

        cursor.execute(
            """
            INSERT INTO documents (file_name, file_type, file_hash, category, uploaded_by)
            VALUES (?, ?, ?, ?, ?)
            """,
            (file_name, file_ext, file_hash, category, current_user["id"])
        )
        doc_id = cursor.lastrowid

        # Insert chunks with mapped FAISS vector IDs
        for idx, (content, vec_id) in enumerate(zip(chunks, vector_ids)):
            cursor.execute(
                """
                INSERT INTO document_chunks (document_id, vector_id, chunk_index, content)
                VALUES (?, ?, ?, ?)
                """,
                (doc_id, vec_id, idx, content)
            )

    return DocumentUploadResponse(
        message="Document ingested",
        chunks_created=len(chunks),
        cache_hit=False
    )


@router.get("", response_model=List[DocumentResponse])
def list_documents(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Returns a list of all ingested documents along with chunk counts and categories.
    Accessible to all authenticated users.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT d.id, d.file_name, d.category, d.created_at, COUNT(c.id) as chunks
            FROM documents d
            LEFT JOIN document_chunks c ON d.id = c.document_id
            GROUP BY d.id
            ORDER BY d.created_at DESC
            """
        )
        rows = cursor.fetchall()

    return [
        DocumentResponse(
            id=row["id"],
            file_name=row["file_name"],
            category=row["category"] or "General",
            chunks=row["chunks"],
            created_at=str(row["created_at"])
        )
        for row in rows
    ]


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Deletes a document, removes its chunks from SQLite, and rebuilds the FAISS vector index.
    Requires Admin privileges.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, file_name FROM documents WHERE id = ?", (document_id,))
        doc = cursor.fetchone()

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found"
            )

        # Delete document (SQLite cascade deletes document_chunks)
        cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))

        # Fetch all remaining chunks to rebuild FAISS index cleanly
        cursor.execute("SELECT id, content FROM document_chunks ORDER BY id ASC")
        remaining_chunks = cursor.fetchall()

    # Rebuild FAISS index
    vstore = get_vector_store()
    if remaining_chunks:
        llm = get_llm_service()
        chunk_texts = [r["content"] for r in remaining_chunks]
        new_embeddings = llm.generate_embeddings(chunk_texts)
        vstore.rebuild(new_embeddings)

        # Update vector IDs in SQLite to match new continuous FAISS indices (0, 1, 2, ...)
        with get_db() as conn:
            cursor = conn.cursor()
            for new_vec_id, r in enumerate(remaining_chunks):
                cursor.execute(
                    "UPDATE document_chunks SET vector_id = ? WHERE id = ?",
                    (new_vec_id, r["id"])
                )
    else:
        vstore.rebuild([])

    return {"message": "Document deleted and index rebuilt"}


@router.post("/reindex")
def reindex_all_documents(
    current_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Explicitly re-indexes all stored document chunks into the FAISS vector store.
    Regenerates vector embeddings from all chunk contents and re-synchronizes vector IDs.
    Requires Admin privileges.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, content FROM document_chunks ORDER BY id ASC")
        chunks = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0]

    vstore = get_vector_store()
    if chunks:
        llm = get_llm_service()
        chunk_texts = [r["content"] for r in chunks]
        new_embeddings = llm.generate_embeddings(chunk_texts)
        vstore.rebuild(new_embeddings)

        with get_db() as conn:
            cursor = conn.cursor()
            for new_vec_id, r in enumerate(chunks):
                cursor.execute(
                    "UPDATE document_chunks SET vector_id = ? WHERE id = ?",
                    (new_vec_id, r["id"])
                )
    else:
        vstore.rebuild([])

    return {
        "message": "Re-indexing complete",
        "documents_indexed": total_docs,
        "chunks_indexed": len(chunks),
        "total_vectors": vstore.total_vectors
    }

