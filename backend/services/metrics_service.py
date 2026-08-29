import io
import csv
import json
from typing import List, Dict, Any, Optional, Union, Generator
import numpy as np
from backend.database import get_db


def log_query(
    user_id: Optional[int],
    query_text: str,
    answer_text: str,
    sources: Union[List[Dict[str, Any]], List[Any], str],
    latency_ms: int,
    cache_hit: bool = False
) -> int:
    """
    Logs a completed search query and its telemetry data to the SQLite query_logs table.

    Parameters:
      - user_id: ID of the user who made the query (optional for anonymous/system queries).
      - query_text: The user's original query.
      - answer_text: The generated answer from the RAG pipeline.
      - sources: List of source citations (dicts or Pydantic models) or a pre-formatted JSON string.
      - latency_ms: Total round-trip execution time in milliseconds.
      - cache_hit: Whether the query or document was served from cache.

    Returns:
      - The integer ID of the newly inserted query_log record.
    """
    if isinstance(sources, (list, dict)):
        # If sources are Pydantic models, convert to dict first
        serializable_sources = [
            s.model_dump() if hasattr(s, "model_dump") else (s.dict() if hasattr(s, "dict") else s)
            for s in sources
        ] if isinstance(sources, list) else sources
        sources_json = json.dumps(serializable_sources)
    else:
        sources_json = str(sources)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO query_logs (user_id, query_text, answer_text, sources_json, latency_ms, cache_hit)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, query_text, answer_text, sources_json, latency_ms, cache_hit)
        )
        return cursor.lastrowid


def get_system_metrics() -> Dict[str, Any]:
    """
    Aggregates telemetry metrics across all documents and past queries.

    Computes:
      - total_documents: Total number of ingested documents.
      - total_chunks: Total number of chunk snippets in FAISS vector store.
      - total_queries_served: Count of all recorded queries in query_logs.
      - latency:
          - median_ms: 50th percentile response time.
          - p95_ms: 95th percentile response time (catches tail latencies).
      - cache_hit_rate_pct: Percentage of operations that hit the cache.

    Returns:
      - Dictionary matching the SystemMetrics Pydantic schema.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Total counts
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM document_chunks")
        total_chunks = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM query_logs")
        total_queries = cursor.fetchone()[0]

        # 2. Query telemetry aggregations
        cursor.execute("SELECT latency_ms, cache_hit FROM query_logs")
        rows = cursor.fetchall()

    if not rows:
        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "total_queries_served": 0,
            "latency": {
                "median_ms": 0.0,
                "p95_ms": 0.0,
            },
            "cache_hit_rate_pct": 0.0,
        }

    latencies = [row["latency_ms"] for row in rows]
    cache_hits = sum(1 for row in rows if bool(row["cache_hit"]))

    # Calculate percentiles using NumPy
    median_latency = float(np.median(latencies))
    p95_latency = float(np.percentile(latencies, 95))
    cache_hit_rate = float((cache_hits / len(rows)) * 100.0)

    return {
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "total_queries_served": total_queries,
        "latency": {
            "median_ms": round(median_latency, 2),
            "p95_ms": round(p95_latency, 2),
        },
        "cache_hit_rate_pct": round(cache_hit_rate, 2),
    }


def generate_query_logs_csv() -> Generator[str, None, None]:
    """
    Generates a CSV export of all recorded query telemetry.
    Yields CSV lines one-by-one as strings for memory-efficient HTTP streaming.

    CSV Columns:
      id, user_id, query_text, answer_text, sources_json, latency_ms, cache_hit, timestamp
    """
    headers = [
        "id",
        "user_id",
        "query_text",
        "answer_text",
        "sources_json",
        "latency_ms",
        "cache_hit",
        "timestamp"
    ]

    # Use io.StringIO to let Python's csv module format row values safely with quotes/escapes
    string_buffer = io.StringIO()
    writer = csv.writer(string_buffer)

    # 1. Yield header line
    writer.writerow(headers)
    yield string_buffer.getvalue()
    string_buffer.seek(0)
    string_buffer.truncate(0)

    # 2. Yield data rows
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, user_id, query_text, answer_text, sources_json, latency_ms, cache_hit, timestamp
            FROM query_logs
            ORDER BY timestamp DESC
            """
        )

        while True:
            rows = cursor.fetchmany(100)
            if not rows:
                break
            for row in rows:
                writer.writerow([
                    row["id"],
                    row["user_id"] if row["user_id"] is not None else "",
                    row["query_text"],
                    row["answer_text"],
                    row["sources_json"],
                    row["latency_ms"],
                    "true" if row["cache_hit"] else "false",
                    row["timestamp"]
                ])
                yield string_buffer.getvalue()
                string_buffer.seek(0)
                string_buffer.truncate(0)
