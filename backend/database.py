import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# Read database path from environment variable, otherwise default to standard store location
DB_PATH = os.getenv("SQLITE_DB_PATH", "backend/data/store/guidely.db")


def get_db_connection() -> sqlite3.Connection:
    """
    Creates and returns a connection to the SQLite database.
    - Ensures the directory exists before connecting.
    - Configures row_factory to sqlite3.Row so results can be accessed like dictionaries.
    - Enables foreign key constraint enforcement in SQLite.
    """
    db_dir = Path(DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    
    # Access columns by name: row['column_name'] instead of row[0]
    conn.row_factory = sqlite3.Row
    
    # SQLite has foreign key constraints disabled by default; enable them explicitly
    conn.execute("PRAGMA foreign_keys = ON;")
    
    return conn


@contextmanager
def get_db():
    """
    Context manager for database operations.
    Automatically handles committing transactions and closing the connection.
    
    Usage:
        with get_db() as conn:
            conn.execute("INSERT INTO ...")
    """
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """
    Initializes the SQLite database and creates the required tables if they do not exist.
    Tables created:
      1. users: User accounts & roles (reader, admin)
      2. documents: Uploaded document records & SHA-256 content hashes
      3. document_chunks: Text snippets mapped to FAISS vector IDs
      4. query_logs: Auto-logged query telemetry, latency, cache hits, and sources
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('reader', 'admin')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Documents Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT UNIQUE NOT NULL,
            file_type TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            uploaded_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 3. Document Chunks Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
            vector_id INTEGER UNIQUE NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL
        );
        """)

        # 4. Query Logs Table (Telemetry)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            query_text TEXT NOT NULL,
            answer_text TEXT NOT NULL,
            sources_json TEXT NOT NULL,
            latency_ms INTEGER NOT NULL,
            cache_hit BOOLEAN NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        print(f"Database initialized successfully at: {DB_PATH}")


if __name__ == "__main__":
    init_db()
