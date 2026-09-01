from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Schema for /health endpoint response."""
    status: str
    database: str
    faiss_vectors: int


class LatencyMetrics(BaseModel):
    """Schema for latency percentile metrics."""
    median_ms: float
    p95_ms: float


class SystemMetrics(BaseModel):
    """Schema for /metrics endpoint response."""
    total_documents: int
    total_chunks: int
    total_queries_served: int
    latency: LatencyMetrics
    cache_hit_rate_pct: float
    repeat_query_hit_rate_pct: float = 100.0
    doc_cache_hit_rate_pct: float = 100.0
