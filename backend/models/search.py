from typing import Optional, List
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Represents a previous message in a conversational thread."""
    role: str  # e.g., 'user' or 'assistant'
    content: str


class SearchQuery(BaseModel):
    """Schema for incoming RAG search requests."""
    query: str
    category_filter: Optional[str] = None
    history: Optional[List[ChatMessage]] = []


class SourceCitation(BaseModel):
    """Schema representing a referenced chunk snippet in the answer."""
    file_name: str
    category: Optional[str] = "general"
    snippet: str
    similarity_score: float


class SearchMetrics(BaseModel):
    """Telemetry information for a single search operation."""
    latency_ms: int
    cache_hit: bool
    retrieved_chunks: int


class SearchResponse(BaseModel):
    """Full structured JSON response for RAG Q&A queries."""
    query: str
    standalone_query: Optional[str] = None
    answer: str
    sources: List[SourceCitation]
    metrics: SearchMetrics
