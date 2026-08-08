# Guidely: Technical Architecture & System Implementation Specification

**Repository URL:** `https://learn.zone01kisumu.ke/git/frawuor/guidely`

**Target Application:** Production-Grade Internal Knowledge Q&A Assistant (RAG Pipeline)

**Tech Stack:** Python 3.10+, FastAPI, SQLite, FAISS, Google Gemini API (`google-genai`), React 18, Vite, Plain CSS Modules.

## 1. Project Overview & Role Play

Guidely is an internal Q&A support engine designed for support engineering and internal operations. It ingests company documents (policies, operational guides, FAQs) across multiple file formats (`.txt`, `.md`, `.pdf`, `.docx`), converts them into 768-dimensional vector embeddings, indexes them using FAISS, and uses Google Gemini to generate natural language answers with source citations.

### System Workflow

1. **Document Ingestion (Admin):** Documents are uploaded, hashed (SHA-256) for cache detection, parsed into text, split into overlapping chunks (~500 tokens), embedded via Gemini API, and indexed into FAISS with metadata stored in SQLite.
2. **Q&A Search (User):** User enters a question (with optional chat history). The backend reformulates follow-ups, embeds the query, searches FAISS for top-$k$ ($k=3$) relevant text chunks, prompts Gemini to draft an answer citing those snippets, and returns structured JSON with auto-logged telemetry metrics.
3. **Role Enforcement:** Reader role can access Search and Q&A; Admin role can access Document Upload, Re-indexing, Category Management, and Telemetry CSV Exports.

## 2. Audit Verification & Requirements Traceability Matrix

To pass the technical audit, the application implements and logs the following metrics:

| **Metric Check** | **Type** | **Target Standard** | **System Implementation Mechanism** |
| --- | --- | --- | --- |
| **Retrieval@3 Accuracy** | Manual | $\ge 80\%$ | FAISS vector search retrieves top 3 chunks. Validated against 15+ standard test queries in sample docs. |
| **Answer Reference Coverage** | Manual | $\ge 90\%$ | System prompt forces Gemini to cite sources. Output JSON maps exact chunk file names and text snippets. |
| **Response Latency** | Auto-Logged | Median $< 3\text{s}$, p95 $< 5\text{s}$ | `query_logs` records request start/end timestamps in milliseconds; exposed via `GET /metrics`. |
| **Cache Effectiveness** | Auto-Logged | $100\%$ on unchanged docs | File content SHA-256 hash comparison in SQLite prevents re-embedding unchanged documents. |
| **Failure Handling** | Auto-Logged | Graceful $4xx/5xx$ JSON | Custom FastAPI exception handlers return standard error structures with user-friendly messages. |
| **Source Precision** | Manual | $\ge 80\%$ | Highlighted snippets verified to directly support generated answers. |

## 3. Directory Structure

```Plaintext
guidely/
├── backend/
│   ├── main.py                  # FastAPI entry point, CORS, startup hooks (Auto-seed Admin)
│   ├── config.py                # Environment variables & configuration defaults
│   ├── database.py              # SQLite connection helper & table initialization
│   ├── models/                  # Pydantic Schemas (Request/Response contracts)
│   │   ├── auth.py              # User register/login & JWT token schemas
│   │   ├── document.py          # Document metadata, upload, & category models
│   │   ├── search.py            # Search query, answer, source citation models
│   │   └── metrics.py           # Health, system metrics, & telemetry schemas
│   ├── services/                # Core Business Logic
│   │   ├── auth_service.py      # Password hashing (bcrypt) & JWT handling (python-jose)
│   │   ├── document_parser.py   # Text, PDF (pypdf), and DOCX (python-docx) extraction & chunking
│   │   ├── vector_store.py      # FAISS index operations, persistence, & SHA-256 hashing
│   │   ├── llm_service.py       # Google Gemini SDK calls (Embeddings & Q&A generation)
│   │   └── metrics_service.py   # Latency stats, hit-rate calculation, CSV export generator
│   ├── routes/                  # API Controllers
│   │   ├── auth.py              # POST /api/auth/register, POST /api/auth/login
│   │   ├── documents.py         # POST, GET, DELETE /api/documents
│   │   ├── search.py            # POST /api/search
│   │   └── system.py            # GET /health, GET /metrics, GET /metrics/export
│   └── data/
│       ├── sample-docs/         # Pre-loaded test documents (policy.txt, faq.txt, guide.txt, etc.)
│       └── store/               # guidely.db (SQLite) & faiss_index.bin (FAISS index)
├── frontend/                    # React + Vite Application
│   ├── public/                  # Static assets
│   ├── src/
│   │   ├── api/                 # Axios/Fetch API client with JWT bearer token interceptor
│   │   ├── assets/              # Icons and styling helpers
│   │   ├── components/          # Reusable UI components
│   │   │   ├── Navbar.jsx       # Navigation header with role badge & logout
│   │   │   ├── ProtectedRoute.jsx # Role-based routing guard
│   │   │   ├── SourceCard.jsx   # Source citation preview component
│   │   │   └── MetricsBadge.jsx # Real-time query performance indicator
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx    # Login / Sign up page
│   │   │   ├── SearchPage.jsx   # Q&A interface with conversation history & category filter
│   │   │   └── AdminPage.jsx    # Document management, file uploader, telemetry dashboard
│   │   ├── App.jsx              # Client-side router configuration
│   │   ├── App.module.css       # Layout styles
│   │   └── main.jsx             # React DOM entry point
│   ├── package.json             # Frontend dependencies
│   └── vite.config.js           # Vite dev server configuration (proxying /api to port 8000)
├── .env                         # Master configuration file (API Keys, JWT Secret)
├── requirements.txt             # Python backend dependencies
└── README.md                    # Project documentation, setup guide, & metrics audit table
```

## 4. Dependencies & Environment Configuration

### Backend `requirements.txt`

```Plaintext
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
pydantic>=2.6.0
pydantic-settings>=2.2.0
google-genai>=0.1.1
faiss-cpu>=1.8.0
numpy>=1.26.0
pypdf>=4.1.0
python-docx>=1.1.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.9
```

### Environment Variables (`.env`)

```Ini
# Core AI Credentials
GEMINI_API_KEY="AIzaSyYourActualGeminiKeyHere"

# Security & JWT Configuration
JWT_SECRET="guidely-super-secret-production-key-change-this-32-chars"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=480

# System Bootstrap Settings
SEED_ADMIN_EMAIL="admin@guidely.com"
SEED_ADMIN_PASSWORD="admin123Password!"

# Data Paths
SQLITE_DB_PATH="backend/data/store/guidely.db"
FAISS_INDEX_PATH="backend/data/store/faiss_index.bin"
```

## 5. Database Schema & Persistence

SQLite database file located at `backend/data/store/guidely.db`.

```sql
-- User Accounts & Role-Based Access Control
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('reader', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Uploaded Documents
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT UNIQUE NOT NULL,
    file_type TEXT NOT NULL,
    file_hash TEXT NOT NULL, -- SHA-256 string for embedding cache detection
    category TEXT DEFAULT 'General',
    uploaded_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Text Chunks mapped to FAISS Vector IDs
CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    vector_id INTEGER UNIQUE NOT NULL, -- Direct index pointer in FAISS
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL
);

-- System Telemetry & Auto-Logged Queries
CREATE TABLE IF NOT EXISTS query_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    query_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    sources_json TEXT NOT NULL, -- JSON array of file names and snippets
    latency_ms INTEGER NOT NULL,
    cache_hit BOOLEAN NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 6. Business Logic & Processing Pipeline

### A. Document Extractor & Chunking (`services/document_parser.py`)

```Python
import hashlib
from typing import List
from pypdf import PdfReader
from docx import Document as DocxDocument

def compute_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def extract_text_from_bytes(file_bytes: bytes, file_type: str) -> str:
    if file_type in ['.txt', '.md']:
        return file_bytes.decode('utf-8', errors='ignore')
    elif file_type == '.pdf':
        import io
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    elif file_type == '.docx':
        import io
        doc = DocxDocument(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs if p.text])
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

def chunk_text(text: str, chunk_size_tokens: int = 500, overlap_tokens: int = 50) -> List[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    step = chunk_size_tokens - overlap_tokens
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size_tokens])
        chunks.append(chunk)
        i += step
    return chunks
```

### B. Gemini API & Embeddings (`services/llm_service.py`)

```Python
import os
from google import genai
from google.genai import types

class GeminiService:
    def __init__(self):
        # Automatically retrieves GEMINI_API_KEY from environment
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.embedding_model = "text-embedding-004"
        self.llm_model = "gemini-1.5-flash"

    def generate_embeddings(self, text_list: list[str]) -> list[list[float]]:
        response = self.client.models.embed_content(
            model=self.embedding_model,
            contents=text_list
        )
        return [e.values for e in response.embeddings]

    def reformulate_query(self, query: str, history: list[dict]) -> str:
        if not history:
            return query

        prompt = (
            "Given the following conversation history and a follow-up question, "
            "rephrase the follow-up question into a standalone query that contains all necessary context.\n\n"
            f"History: {history}\n"
            f"Follow-up question: {query}\n"
            "Standalone query:"
        )
        response = self.client.models.generate_content(
            model=self.llm_model,
            contents=prompt
        )
        return response.text.strip()

    def generate_answer(self, query: str, context_chunks: list[dict]) -> str:
        context_str = "\n\n".join([
            f"Source File: {c['file_name']}\nSnippet: {c['content']}"
            for c in context_chunks
        ])

        system_instruction = (
            "You are Guidely, an internal support Q&A assistant. "
            "Answer the user's question clearly and concisely using ONLY the provided document snippets below. "
            "If the answer cannot be found in the snippets, explicitly state: 'I could not find the answer in the available documentation.' "
            "Always include source file references in your answer when stating facts."
        )

        full_prompt = f"Context:\n{context_str}\n\nUser Question: {query}"

        response = self.client.models.generate_content(
            model=self.llm_model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2
            )
        )
        return response.text
```

### C. FAISS Vector Store Management (`services/vector_store.py`)

```Python
import os
import faiss
import numpy as np

class FAISSManager:
    def __init__(self, index_path: str, dimension: int = 768):
        self.index_path = index_path
        self.dimension = dimension
        if os.path.exists(index_path):
            self.index = faiss.read_index(index_path)
        else:
            self.index = faiss.IndexFlatIP(dimension) # Inner Product (Cosine Similarity on normalized vectors)

    def save(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)

    def add_vectors(self, vectors: list[list[float]]) -> list[int]:
        norm_vectors = np.array(vectors, dtype=np.float32)
        faiss.normalize_L2(norm_vectors)
        start_id = self.index.ntotal
        self.index.add(norm_vectors)
        self.save()
        return list(range(start_id, self.index.ntotal))

    def search(self, query_vector: list[float], k: int = 3) -> tuple[list[int], list[float]]:
        if self.index.ntotal == 0:
            return [], []
        norm_vector = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(norm_vector)
        distances, indices = self.index.search(norm_vector, k)
        return indices[0].tolist(), distances[0].tolist()

    def rebuild(self, all_vectors: list[list[float]]):
        self.index = faiss.IndexFlatIP(self.dimension)
        if all_vectors:
            self.add_vectors(all_vectors)
        else:
            self.save()
```

## 7. API Route Definitions & Contracts

### Auth Endpoints (`/api/auth`)

- `POST /api/auth/register`
    - **Request Body:** `{"email": "user@guidely.com", "password": "password123"}`
    - **Response:** `201 Created` $\rightarrow$ `{"id": 2, "email": "user@guidely.com", "role": "reader"}`
- `POST /api/auth/login`
    - **Request Body:** `{"email": "admin@guidely.com", "password": "admin123Password!"}`
    - **Response:** `200 OK` $\rightarrow$ `{"access_token": "jwt_token_string", "token_type": "bearer", "role": "admin"}`

### Document Endpoints (`/api/documents`)

- `POST /api/documents` *(Admin Role Required)*
    - **Form Data:** `file: UploadFile`, `category: str = "General"`
    - **Response (Cache Hit):** `200 OK` $\rightarrow$ `{"message": "File unchanged. Embedding skipped.", "cache_hit": true}`
    - **Response (New File):** `201 Created` $\rightarrow$ `{"message": "Document ingested", "chunks_created": 8, "cache_hit": false}`
- `GET /api/documents` *(Authenticated)*
    - **Response:** `200 OK` $\rightarrow$ `[{"id": 1, "file_name": "policy.txt", "category": "HR", "chunks": 5, "created_at": "2026-08-08..."}]`
- `DELETE /api/documents/{id}` *(Admin Role Required)*
    - **Response:** `200 OK` $\rightarrow$ `{"message": "Document deleted and index rebuilt"}`

### Search Endpoint (`/api/search`)

- `POST /api/search` *(Authenticated)*
    - **Request Body:**
        
        ```JSON
        {
          "query": "How many days of PTO do I get?",
          "category_filter": "HR",
          "history": [
            {"role": "user", "content": "Tell me about time off."},
            {"role": "assistant", "content": "We offer sick leave and paid time off."}
          ]
        }
        ```
        
    - **Response:** `200 OK`
        
        ```JSON
        {
          "query": "How many days of PTO do I get?",
          "standalone_query": "How many days of paid time off do full-time employees get according to HR policy?",
          "answer": "Full-time employees receive 20 days of paid time off (PTO) annually according to policy.txt.",
          "sources": [
            {
              "file_name": "policy.txt",
              "category": "HR",
              "snippet": "Paid Time Off (PTO): Full-time employees receive 20 days per calendar year...",
              "similarity_score": 0.884
            }
          ],
          "metrics": {
            "latency_ms": 1240,
            "cache_hit": true,
            "retrieved_chunks": 3
          }
        }
        ```
        

### System Endpoints (`/api/system`)

- `GET /health` $\rightarrow$ `{"status": "healthy", "database": "connected", "faiss_vectors": 42}`
- `GET /metrics` $\rightarrow$
    
    ```JSON
    {
      "total_documents": 5,
      "total_chunks": 38,
      "total_queries_served": 112,
      "latency": {
        "median_ms": 1150,
        "p95_ms": 2300
      },
      "cache_hit_rate_pct": 100.0
    }
    ```
    
- `GET /metrics/export` *(Admin Role Required)* $\rightarrow$ Streams `query_logs.csv` download file.

## 8. Setup & Quickstart Commands

### 1. Backend Setup

```Bash
# Navigate to repository root
cd guidely

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment file
cp .env.example .env # Ensure GEMINI_API_KEY is populated inside .env

# Run FastAPI Server (auto-creates database and seeds admin)
uvicorn backend.main:app --reload --port 8000
```

### 2. Frontend Setup

```Bash
# In a new terminal window
cd guidely/frontend

# Install dependencies
npm install

# Start Vite Development Server
npm run dev
```

Access the web interface at `http://localhost:5173`. Log in using the auto-seeded credentials:

- **Email:** `admin@guidely.com`
- **Password:** `admin123Password!`