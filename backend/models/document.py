from typing import Optional
from pydantic import BaseModel


class DocumentCategoryUpdate(BaseModel):
    """Schema for updating a document's assigned category."""
    category: str


class DocumentUploadResponse(BaseModel):
    """Schema returned after document upload / ingestion."""
    message: str
    chunks_created: Optional[int] = None
    cache_hit: bool


class DocumentResponse(BaseModel):
    """Schema representing document metadata returned in document listings."""
    id: int
    file_name: str
    category: str
    chunks: int
    created_at: str
