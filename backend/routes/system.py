from typing import Dict, Any
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from backend.models.metrics import HealthResponse, SystemMetrics
from backend.routes.auth import require_admin
from backend.routes.documents import get_vector_store
from backend.services.metrics_service import get_system_metrics, generate_query_logs_csv
from backend.database import get_db

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse)
@router.get("/api/health", response_model=HealthResponse)
def health_check():
    """
    Returns system operational health status, database connectivity,
    and indexed vector count.
    """
    db_status = "disconnected"
    try:
        with get_db() as conn:
            conn.execute("SELECT 1")
            db_status = "connected"
    except Exception:
        db_status = "error"

    vstore = get_vector_store()
    vector_count = vstore.total_vectors

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        faiss_vectors=vector_count
    )


@router.get("/metrics", response_model=SystemMetrics)
@router.get("/api/metrics", response_model=SystemMetrics)
def system_metrics():
    """
    Returns system telemetry metrics including total documents, total chunks,
    queries served, median/p95 response latencies, and cache hit rates.
    """
    metrics_data = get_system_metrics()
    return SystemMetrics(**metrics_data)


@router.get("/metrics/export")
@router.get("/api/metrics/export")
def export_telemetry_csv(current_user: Dict[str, Any] = Depends(require_admin)):
    """
    Streams recorded query logs as a downloadable CSV file.
    Requires Admin privileges.
    """
    csv_stream = generate_query_logs_csv()
    response = StreamingResponse(
        csv_stream,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=query_logs.csv",
            "Cache-Control": "no-cache"
        }
    )
    return response
