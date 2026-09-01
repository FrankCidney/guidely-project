import time
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status, Depends
from backend.models.search import SearchQuery, SearchResponse, SourceCitation, SearchMetrics
from backend.routes.auth import get_current_user
from backend.routes.documents import get_vector_store, get_llm_service, sanitize_category
from backend.services.metrics_service import log_query
from backend.database import get_db

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
def perform_search(
    request: SearchQuery,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Core RAG Search & Q&A Pipeline:
      1. Reformulates conversational follow-up questions if chat history is provided.
      2. Generates a 768-dimensional embedding of the standalone query.
      3. Performs FAISS Inner-Product similarity search for top-k (k=3) matching chunks.
      4. Retrieves matching document text snippets from SQLite (with optional category filter).
      5. Synthesizes a grounded answer citing exact source files using Gemini.
      6. Automatically records telemetry performance metrics (latency, citations, cache hit).
    """
    raw_query = request.query.strip()
    if not raw_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty"
        )

    start_time = time.perf_counter()
    vstore = get_vector_store()
    llm = get_llm_service()

    # 1. Conversational Query Reformulation
    if request.history:
        # If this exact query is already cached, reuse it directly to guarantee 100% repeat cache hits and reduce latency
        if llm.get_cached_embedding(raw_query) is not None:
            standalone_query = raw_query
        else:
            standalone_query = llm.reformulate_query(raw_query, request.history)
    else:
        standalone_query = raw_query

    # 2. Query Embedding (with persistent SQLite caching)
    try:
        query_vector, cache_hit = llm.get_query_embedding(standalone_query)
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Google Gemini API Quota Exceeded (429): Embedding rate limit reached. Please wait a moment or use another API key."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate query embedding: {err_str}"
        )

    # 3. Vector Similarity Search (Top-k=3)
    # Search for more if category filter is active to ensure enough matches
    search_k = 6 if request.category_filter else 3
    matched_indices, scores = vstore.search(query_vector, k=search_k)

    # 4. Fetch context chunks from SQLite
    context_chunks = []
    citations: List[SourceCitation] = []

    if matched_indices and vstore.total_vectors > 0:
        # Filter out negative indices FAISS returns when index has fewer vectors than k
        valid_pairs = [(idx, score) for idx, score in zip(matched_indices, scores) if idx >= 0]

        if valid_pairs:
            score_map = {idx: score for idx, score in valid_pairs}
            vector_ids = list(score_map.keys())

            placeholders = ",".join("?" for _ in vector_ids)
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    SELECT c.vector_id, c.content, d.file_name, d.category
                    FROM document_chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE c.vector_id IN ({placeholders})
                    """,
                    vector_ids
                )
                rows = cursor.fetchall()

            # Map rows with their similarity score and apply optional category filter
            retrieved = []
            clean_filter = sanitize_category(request.category_filter) if request.category_filter else None
            for r in rows:
                category = sanitize_category(r["category"])
                if clean_filter and category != clean_filter:
                    continue

                sim_score = float(score_map.get(r["vector_id"], 0.0))
                retrieved.append({
                    "file_name": r["file_name"],
                    "category": category,
                    "content": r["content"],
                    "similarity_score": sim_score
                })

            # Sort by highest similarity score and cap at top 3
            retrieved.sort(key=lambda x: x["similarity_score"], reverse=True)
            top_chunks = retrieved[:3]

            context_chunks = top_chunks
            citations = [
                SourceCitation(
                    file_name=c["file_name"],
                    category=c["category"],
                    snippet=c["content"],
                    similarity_score=round(c["similarity_score"], 3)
                )
                for c in top_chunks
            ]

    # 5. Answer Generation via Gemini with strict grounding
    try:
        answer = llm.generate_answer(standalone_query, context_chunks)
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Google Gemini API Quota Exceeded (429): Rate limit reached for the active model. Please wait a moment, change GEMINI_LLM_MODEL in .env, or use another API key."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {err_str}"
        )

    # 6. Telemetry Logging & Performance Metrics
    end_time = time.perf_counter()
    latency_ms = max(1, int((end_time - start_time) * 1000))

    log_query(
        user_id=current_user.get("id"),
        query_text=raw_query,
        answer_text=answer,
        sources=citations,
        latency_ms=latency_ms,
        cache_hit=cache_hit
    )

    metrics = SearchMetrics(
        latency_ms=latency_ms,
        cache_hit=cache_hit,
        retrieved_chunks=len(citations)
    )

    return SearchResponse(
        query=raw_query,
        standalone_query=standalone_query if standalone_query != raw_query else None,
        answer=answer,
        sources=citations,
        metrics=metrics
    )
