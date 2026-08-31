# Guidely: Production-Grade Internal Knowledge Q&A Assistant

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![FAISS](https://img.shields.io/badge/Vector%20Store-FAISS-00599C.svg)](https://github.com/facebookresearch/faiss)
[![Google Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-4285F4.svg)](https://ai.google.dev/)
[![React + Vite](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB.svg)](https://vitejs.dev/)

---

## 1. Project Overview

**Guidely** is an internal enterprise Knowledge Q&A assistant built for support engineering, IT, and internal operations. It implements an end-to-end Retrieval-Augmented Generation (RAG) pipeline designed to ingest company documents (policies, runbooks, FAQs, guidelines), extract and chunk their content, generate high-dimensional semantic embeddings, index them into a high-performance vector store, and provide grounded answers with exact source citations via Google Gemini.

### Key Capabilities & Workflow

1. **Multi-Format Ingestion:** Ingests documentation across `.txt`, `.md`, `.pdf` (via `pypdf`), and `.docx` (via `python-docx`).
2. **SHA-256 Content Hashing & Cache Detection:** Prevents unnecessary embedding recomputation by calculating content hashes; unchanged files skip embedding generation with a 100% cache-hit response.
3. **Chunking & Vector Indexing:** Splits text into overlapping semantic chunks (~500 tokens with 50-token overlap), generates 768-dimensional normalized embeddings via Google Gemini (`text-embedding-004`), and indexes them in FAISS (`IndexFlatIP`).
4. **Contextual Query Reformulation:** Reformulates multi-turn conversational follow-up questions into standalone queries using `gemini-1.5-flash` before vector lookup.
5. **Grounded Answer Generation:** Prompts Gemini with retrieved top-$k$ ($k=3$) snippets under strict system instructions to cite exact file names and prevent hallucinations.
6. **Role-Based Access Control (RBAC):**
   - **Reader:** Search and conversational Q&A, category filtering, viewing citations, and query performance badges.
   - **Admin:** Document upload, deletion, index rebuilding, category assignment, real-time system metrics, and CSV telemetry export.
7. **Telemetry & Audit Logging:** Automatically logs query latency, token usage, similarity scores, and cache hits in SQLite.

---

## 2. Tech Stack

- **Backend:** Python 3.10+, FastAPI, Uvicorn, SQLite3, FAISS (`faiss-cpu`), Google Gemini SDK (`google-genai`), Pydantic v2, PyPDF, python-docx, python-jose (JWT), Passlib (bcrypt).
- **Frontend:** React 19, Vite, Axios (with automatic Bearer token interceptor), Lucide React, CSS Modules.
- **AI Models:**
  - Embeddings: `text-embedding-004` (768 dimensions)
  - Chat & Generation: `gemini-1.5-flash`

---

## 3. Audit Verification & Requirements Traceability Matrix

| **Metric Check** | **Type** | **Target Standard** | **System Implementation Mechanism** |
| :--- | :--- | :--- | :--- |
| **Retrieval@3 Accuracy** | Manual | $\ge 80\%$ | FAISS vector search retrieves top 3 chunks. Validated against sample docs across test queries. |
| **Answer Reference Coverage** | Manual | $\ge 90\%$ | System prompt forces Gemini to cite sources. Output JSON maps exact chunk file names and text snippets. |
| **Response Latency** | Auto-Logged | Median $< 3\text{s}$, p95 $< 5\text{s}$ | `query_logs` records request start/end timestamps in milliseconds; exposed via `GET /metrics`. |
| **Cache Effectiveness** | Auto-Logged | $100\%$ on unchanged docs | File content SHA-256 hash comparison in SQLite prevents re-embedding unchanged documents. |
| **Failure Handling** | Auto-Logged | Graceful $4xx/5xx$ JSON | Custom FastAPI exception handlers return standard error structures with user-friendly messages. |
| **Source Precision** | Manual | $\ge 80\%$ | Highlighted snippets verified to directly support generated answers. |

---

## 4. Directory Structure

```plaintext
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
│       ├── sample-docs/         # Pre-loaded test documents (PDF, DOCX, TXT)
│       └── store/               # guidely.db (SQLite) & faiss_index.bin (FAISS index)
├── frontend/                    # React + Vite Application
│   ├── src/
│   │   ├── api/                 # Axios client with JWT bearer token interceptor
│   │   ├── components/          # Navbar, ProtectedRoute, SourceCard, MetricsBadge
│   │   ├── pages/               # LoginPage, SearchPage, AdminPage
│   │   ├── App.jsx              # Router & Route guards
│   │   └── main.jsx             # React entry point
│   ├── package.json             # Frontend dependencies
│   └── vite.config.js           # Vite dev server with proxy to backend port 8000
├── .env.example                 # Example configuration file
├── requirements.txt             # Python backend dependencies
├── setup_backend.sh             # Automated backend non-sudo setup script
└── README.md                    # Project documentation
```

---

## 5. Setup & How to Run

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** & **npm**
- **Google Gemini API Key** ([Google AI Studio](https://aistudio.google.com/))

---

### Step 1: Configure Environment Variables

In the project root directory, copy the example environment file and configure your API key:

```bash
cp .env.example .env
```

Edit `.env` and supply your Gemini API key:
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

### Step 2: Backend Setup & Startup

#### Option A: Automated Non-Sudo Script (Recommended)
If running on systems where `python3-venv` is missing and you lack `sudo` access, run the automated setup script:

```bash
# Run the setup script
./setup_backend.sh

# Activate virtual environment and start FastAPI
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

#### Option B: Manual Setup
```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Start FastAPI server
uvicorn backend.main:app --reload --port 8000
```

- Backend URL: `http://127.0.0.1:8000`
- Interactive API Docs (Swagger): `http://127.0.0.1:8000/docs`
- Health Endpoint: `http://127.0.0.1:8000/health`

---

### Step 3: Frontend Setup & Startup

Open a **separate terminal window**:

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start the Vite development server
npm run dev
```

- Frontend URL: `http://localhost:5173`

---

## 6. Initial Application Walkthrough

### 1. Admin Login & Ingestion
1. Open `http://localhost:5173` in your browser.
2. Sign in with default administrator credentials:
   - **Email:** `admin@guidely.com`
   - **Password:** `admin123Password!`
3. Navigate to the **Admin Dashboard** (`/admin`).
4. Ingest sample documents from `backend/data/sample-docs/`:
   - `sample-docs_hr_pto_and_leave_policy.pdf` (Category: `HR`)
   - `sample-docs_hr_remote_work_and_stipends.docx` (Category: `HR`)
   - `sample-docs_it_access_and_security_guide.pdf` (Category: `IT`)
   - `sample-docs_it_oncall_and_incident_runbook.txt` (Category: `IT`)
   - `sample-docs_general_expenses_and_office_faq.docx` (Category: `General`)

### 2. Q&A Search Interface
1. Navigate to the **Search** tab (`/search`).
2. Ask questions against your ingested documentation:
   - *"How many days of PTO do full-time employees receive?"*
   - *"What are the requirements for home office stipends?"*
   - *"How do I escalate an IT production outage?"*
3. View the grounded answer, similarity scores, highlighted snippet cards, and query telemetry badge.

---

## 7. API Endpoints Reference

### Authentication (`/api/auth`)
- `POST /api/auth/register` - Create reader account (`{"email": "...", "password": "..."}`)
- `POST /api/auth/login` - Authenticate and obtain JWT Bearer token

### Documents (`/api/documents`)
- `POST /api/documents` - *(Admin only)* Ingest document file with category and SHA-256 cache check
- `GET /api/documents` - List all indexed documents with chunk counts and categories
- `DELETE /api/documents/{id}` - *(Admin only)* Remove document and rebuild FAISS index

### Search & Q&A (`/api/search`)
- `POST /api/search` - Perform conversational RAG query with optional category filter and chat history

### System & Metrics (`/api/system` / Root)
- `GET /health` - System health check (DB connection & vector count)
- `GET /metrics` - Performance metrics (median/p95 latency, total queries, cache hit rate)
- `GET /metrics/export` - *(Admin only)* Stream and download `query_logs.csv`
