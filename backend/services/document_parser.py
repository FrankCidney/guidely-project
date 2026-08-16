import io
import hashlib
from typing import List
from pypdf import PdfReader
from docx import Document as DocxDocument


def compute_sha256(file_bytes: bytes) -> str:
    """
    Computes the SHA-256 cryptographic hash of raw file bytes.
    Used in RAG pipelines to detect duplicate/unchanged files and skip redundant re-embedding
    """
    return hashlib.sha256(file_bytes).hexdigest()

def extract_text_from_bytes(file_bytes: bytes, file_type: str) -> str:
    """
    Extracts raw plain text from different document file formats.
    Supported formats:
      - .txt, .md: Plain text decoding (UTF-8)
      - .pdf: Extracted page-by-page using pypdf
      - .docx: Extracted paragraph-by-paragraph using python-docx
    """
    normalized_type = file_type.lower()
    if not normalized_type.startswith('.'):
            normalized_type = f".{normalized_type}"

    if normalized_type in ['.txt','.md']:
        return file_bytes.decode('utf-8', errors='ignore')

    elif normalized_type == '.pdf':
            reader = PdfReader(io.BytesIO(file_bytes))
            extracted_pages = [
                page.extract_text()
                for page in reader.pages
                if page.extract_text()
            ]
            return "\n".join(extracted_pages)

    elif normalized_type == ".docx":
            doc = DocxDocument(io.BytesIO(file_bytes))
            extracted_paragraphs = [
                p.text
                for p in doc.paragraphs
                if p.text
            ]
            return "\n".join(extracted_paragraphs)

    else:
            raise ValueError(f"Unsupported file type: {file_type}. Supported: .txt, .md, .pdf, .docx")


def chunk_text(text: str, chunk_size_tokens: int = 500, overlap_tokens: int = 50) -> List[str]:
    """
    Splits text into overlapping chunks.
    
    Overlap is important in RAG because hard-splitting could break context if a key piece of information ends up at word 499 out of 500 for example.
    It could split important context between chunk A and B.
    """
    words = text.split()
    if not words:
        return []

    # If document is smaller than chunk size, return the whole text as a single chunk
    if len(words) <= chunk_size_tokens:
          return [" ".join(words)]
    
    chunks = []
    i = 0
    step = max(1, chunk_size_tokens - overlap_tokens)

    while i < len(words):
          chunk = " ".join(words[i:i + chunk_size_tokens])
          chunks.append(chunk)
          i += step

    return chunks