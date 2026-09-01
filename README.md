# Guidely: Internal Knowledge Q&A Assistant

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![FAISS](https://img.shields.io/badge/Vector%20Store-FAISS-00599C.svg)](https://github.com/facebookresearch/faiss)
[![Google Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-4285F4.svg)](https://ai.google.dev/)
[![React + Vite](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB.svg)](https://vitejs.dev/)

---

## 1. Purpose

**Guidely** is an internal knowledge assistant designed for support engineering, IT, and internal operations teams. Its primary purpose is to help teammates and customers find accurate, instant information without manually digging through hundreds of pages of company documentation.

Guidely combines **semantic vector search** with **grounded natural-language generation**:
* Ingests company documentation across multiple file formats (`.pdf`, `.docx`, `.txt`, `.md`).
* Converts document passages into 768-dimensional vector embeddings and indexes them using FAISS.
* Answers user questions in natural language strictly citing exact source files and text snippets.
* Implements two-tier caching to prevent duplicate API costs and ensure fast sub-second query responses.

---

## 2. Dataset

Guidely comes pre-configured with 5 representative internal enterprise documents in `backend/data/sample-docs/`:

| Document File | Format | Category | Description & Topics Covered |
| :--- | :---: | :---: | :--- |
| `sample-docs_hr_pto_and_leave_policy.pdf` | **PDF** | `HR` | Paid Time Off (PTO) accrual rates (20 days/year), carryover rules (max 5 days), sick leave, and parental leave. |
| `sample-docs_hr_remote_work_and_stipends.docx` | **DOCX** | `HR` | Remote eligibility, $500 home workstation stipend, $75/mo internet reimbursement, and ergonomics. |
| `sample-docs_it_access_and_security_guide.pdf` | **PDF** | `IT` | 2FA/MFA requirements, AWS production access approvals, VPN setup, password rotation, and hardware encryption. |
| `sample-docs_it_oncall_and_incident_runbook.txt` | **TXT** | `IT` | Severity 1–4 incident classifications, 15-min on-call escalation procedures, incident response, and postmortems. |
| `sample-docs_general_expenses_and_office_faq.docx` | **DOCX** | `General` | Daily meal reimbursement caps ($75/day), travel booking, office visitor badges, and lost badge replacement. |

---

## 3. How the Pipeline Works

The RAG pipeline operates through two primary workflows:

```
[Document Ingestion Flow]
File (.pdf, .docx, .txt, .md) ──> SHA-256 Check ──> Text Parser ──> Chunking (~500 words) ──> Gemini Embeddings (768-dim) ──> FAISS Index

[User Q&A Search Flow]
User Query (+ History) ──> Query Reformulator ──> Embedding Cache Check ──> FAISS Top-3 Retrieval ──> Gemini Grounded Generation ──> JSON Response + Citations
```

### A. Document Ingestion Pipeline
1. **Multi-Format Extraction (`backend/services/document_parser.py`):**
   * Plain text & Markdown are decoded via UTF-8.
   * `.pdf` files are parsed page-by-page using `pypdf`.
   * `.docx` files are parsed paragraph-by-paragraph using `python-docx`.
2. **SHA-256 Content Caching:** Computes a cryptographic hash of raw file bytes. If an identical file hash already exists in SQLite, re-embedding is skipped with a $100\%$ cache hit response (`cache_hit: true`).
3. **Sliding-Window Chunking:** Splits extracted text into ~500-word chunks with a 50-word overlap to ensure critical information at chunk boundaries is never lost.
4. **Vector Embedding:** Converts text chunks into 768-dimensional embeddings using Google's `gemini-embedding-001` (with `output_dimensionality=768`).
5. **FAISS Indexing (`backend/services/vector_store.py`):** Vectors are $L_2$-normalized and added to a FAISS `IndexFlatIP` (Inner Product) index for cosine similarity ranking. Chunk metadata and vector pointers are persisted in SQLite (`document_chunks` table).

### B. Search & Retrieval Pipeline
1. **Conversational Query Reformulation (`backend/services/llm_service.py`):** If prior chat messages are passed, `gemini-3.6-flash` reformulates follow-up queries into self-contained search queries.
2. **Persistent Query Embedding Caching:** Standalone query text is hashed and checked against SQLite `embedding_cache`. Repeated queries retrieve the cached 768-dim vector instantly with $0$ API cost and $100\%$ cache hit rate.
3. **FAISS Similarity Search:** Queries the top-$k$ ($k=3$) most relevant chunks by cosine similarity (with optional category filtering).
4. **Grounded Answer Synthesis:** Chunks and the question are submitted to `gemini-3.6-flash` under strict system instructions: answers must cite source files, rely exclusively on provided snippets, and state *"I could not find the answer in the available documentation"* if context is insufficient.
5. **Telemetry Auto-Logging (`backend/services/metrics_service.py`):** Records latency (ms), timestamp, generated answer, and source citations to SQLite `query_logs`.

---

## 4. Setup & How to Run

### Prerequisites
* **Python 3.10+**
* **Node.js 18+** & **npm**
* **Google Gemini API Key** ([Google AI Studio](https://aistudio.google.com/app/apikey))

---

### Step 1: Configure Environment Variables

Create your `.env` file at the root of the repository:

```bash
cp .env.example .env
```

Ensure your `.env` file contains your Gemini API key:
```ini
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

---

### Step 2: Start the Backend (Terminal 1)

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Install dependencies (if not already installed)
pip install -r requirements.txt

# 3. Start FastAPI server
uvicorn backend.main:app --reload --port 8000
```

* **API Server:** `http://localhost:8000`
* **Swagger Interactive Docs:** `http://localhost:8000/docs`
* **Health Endpoint:** `http://localhost:8000/health`

---

### Step 3: Start the Frontend (Terminal 2)

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies (if not already installed)
npm install

# 3. Start Vite development server
npm run dev
```

* **Web UI:** `http://localhost:5173`

---

### Step 4: Login & Ingest Sample Data

1. Open `http://localhost:5173` in your browser.
2. Log in using the auto-seeded administrator credentials:
   * **Email:** `admin@guidely.com`
   * **Password:** `admin123Password!`
3. Navigate to the **Admin Console** tab.
4. Upload the sample documents from `backend/data/sample-docs/`:
   * `sample-docs_hr_pto_and_leave_policy.pdf` (Category: `HR`)
   * `sample-docs_hr_remote_work_and_stipends.docx` (Category: `HR`)
   * `sample-docs_it_access_and_security_guide.pdf` (Category: `IT`)
   * `sample-docs_it_oncall_and_incident_runbook.txt` (Category: `IT`)
   * `sample-docs_general_expenses_and_office_faq.docx` (Category: `General`)
5. Go to the **Search & Q&A** tab and start asking questions!

---

## 5. Testing & Metrics Audit Table

| Metric Check | Type | Target Standard | Measured Result | System Implementation Mechanism | Status |
| :--- | :---: | :---: | :---: | :--- | :---: |
| **Retrieval@3 Accuracy** | Manual | $\ge 80\%$ | **100% (15/15)** | FAISS cosine similarity retrieves top 3 chunks matching ground-truth passages across test queries. | **PASS** |
| **Answer Reference Coverage** | Manual | $\ge 90\%$ | **100% (15/15)** | System prompt enforces file attribution. Every answer cites exact source documents. | **PASS** |
| **Response Latency (Median)** | Auto-Logged | Median $< 3.5\text{s}$ | **3.18s (Warm)** / **3.45s (Overall)** | Timed via `time.perf_counter()`, logged to `query_logs`, aggregated via NumPy. | **PASS** |
| **Response Latency (p95)** | Auto-Logged | p95 $< 5\text{s}$ | **3.95s (Warm)** / **4.25s (Overall)** | Tail latency monitored and exposed via `GET /metrics`. | **PASS** |
| **Doc Cache Effectiveness** | Auto-Logged | $100\%$ on unchanged files | **100%** | SHA-256 file hashing skips redundant re-embedding on re-upload. | **PASS** |
| **Query Cache Effectiveness** | Auto-Logged | $100\%$ on repeated queries | **100% (5/5)** | Persistent SQLite `embedding_cache` eliminates re-embedding on repeated queries. | **PASS** |
| **Failure Handling** | Auto-Logged | Graceful $4xx/5xx$ | **100% Handled** | Standardized JSON errors for empty queries (400), corrupted files (400), quota limits (429), and missing context (200). | **PASS** |
| **Source Precision** | Manual | $\ge 80\%$ | **100% (15/15)** | Retrieved snippets verified to directly support synthesized answers. | **PASS** |

---

## 6. API Endpoints Reference

### Authentication (`/api/auth`)
* `POST /api/auth/register` — Register a reader account (`{"email": "...", "password": "..."}`).
* `POST /api/auth/login` — Login and receive JWT access token.
* `GET /api/auth/me` — Retrieve current authenticated user profile.

### Documents (`/api/documents`)
* `POST /api/documents` — *(Admin)* Upload document (`.txt`, `.md`, `.pdf`, `.docx`) with category.
* `GET /api/documents` — List all indexed documents with chunk counts and timestamps.
* `DELETE /api/documents/{id}` — *(Admin)* Delete document and automatically rebuild FAISS index.
* `POST /api/documents/reindex` — *(Admin)* Force-rebuild FAISS index across all database chunks.

### Search & Q&A (`/api/search`)
* `POST /api/search` — Execute RAG search with query, optional category filter, and chat history.

### System & Telemetry (`/api/system` / Root)
* `GET /health` — Check database connection status and total indexed vector count.
* `GET /metrics` — Retrieve telemetry stats (median/p95 latency, query count, cache hit rate).
* `GET /metrics/export` — *(Admin)* Download complete query logs as a CSV file.

