# Guidely Implementation Checklist

---

### Phase 1: Environment & Directory Setup

* [x] Create root project directory structure (`backend/`, `frontend/`, `data/`)


* [x] Initialize React/Vite app in `frontend/`

* [x] Create core backend files (`requirements.txt`, `.env`, `.gitignore`)


* [x] Set up Python virtual environment and install backend dependencies (`fastapi`, `google-genai`, `faiss-cpu`, `pypdf`, `python-docx`)


* [x] Populate sample test files in `backend/data/sample-docs/` (`policy.txt`, `faq.txt`, `guide.txt`)



---

### Phase 2: Database Schema & Data Models

* [ ] Implement `backend/database.py` with SQLite connection initialization


* [ ] Create SQLite schema tables in `database.py`:
* [ ] `users` (id, email, hashed_password, role, created_at)


* [ ] `documents` (id, file_name, file_type, file_hash, category, uploaded_by, created_at)


* [ ] `document_chunks` (id, document_id, vector_id, chunk_index, content)


* [ ] `query_logs` (id, user_id, query_text, answer_text, sources_json, latency_ms, cache_hit, timestamp)




* [ ] Build Pydantic schemas in `backend/models/`:
* [ ] `auth.py` (UserRegister, UserLogin, TokenResponse, UserOut)


* [ ] `document.py` (DocumentResponse, DocumentCategoryUpdate)


* [ ] `search.py` (SearchQuery, SearchResponse, SourceCitation)


* [ ] `metrics.py` (HealthResponse, SystemMetrics)





---

### Phase 3: Core Business Services

* [ ] `services/auth_service.py`: Password hashing (bcrypt) and JWT generation/verification


* [ ] `services/document_parser.py`:
* [ ] SHA-256 hash calculator for document content


* [ ] Text extraction handlers for `.txt`, `.md`, `.pdf` (`pypdf`), and `.docx` (`python-docx`)


* [ ] Token-based chunking logic (~500 tokens per chunk with 50-token overlap)




* [ ] `services/vector_store.py`:
* [ ] FAISS index manager (`IndexFlatIP` for 768-dimensional normalized vectors)


* [ ] Methods to add vectors, persist to `faiss_index.bin`, query top-k, and rebuild index




* [ ] `services/llm_service.py`:
* [ ] Google Gemini API wrapper (`google-genai`) using `text-embedding-004`

* [ ] Conversational query reformulation for follow-up questions using `gemini-1.5-flash`

* [ ] Context-augmented Q&A answer generation with strict citation constraints




* [ ] `services/metrics_service.py`:
* [ ] Metric calculation logic (median latency, p95 latency, cache hit rates)


* [ ] Query log writer and CSV export stream generator





---

### Phase 4: Backend API Routes & FastAPI Entry

* [ ] Build API Controllers in `backend/routes/`:
* [ ] `routes/auth.py`: `POST /api/auth/register`, `POST /api/auth/login`

* [ ] `routes/documents.py`: `POST /api/documents` (with SHA-256 cache-hit skip), `GET /api/documents`, `DELETE /api/documents/{id}`

* [ ] `routes/search.py`: `POST /api/search` (vector query, LLM execution, telemetry logging)


* [ ] `routes/system.py`: `GET /health`, `GET /metrics`, `GET /metrics/export`



* [ ] Implement `backend/main.py`:
* [ ] CORS middleware setup


* [ ] Application startup event to initialize database tables and auto-seed admin user (`SEED_ADMIN_EMAIL`)


* [ ] Global exception handlers for standard `4xx`/`5xx` error JSON responses





---

### Phase 5: Frontend React Implementation

* [ ] Setup Axios API client (`src/api/client.js`) with automatic JWT Bearer header interceptor


* [ ] Build shared UI Components:
* [ ] `Navbar.jsx` (Navigation bar showing user role badge & logout button)


* [ ] `ProtectedRoute.jsx` (Route guard enforcing authentication and role limits)


* [ ] `SourceCard.jsx` (Component displaying cited source files, snippets, and match confidence)


* [ ] `MetricsBadge.jsx` (Query response latency and cache state display)




* [ ] Build Views & Pages:
* [ ] `LoginPage.jsx` (User authentication and signup interface)


* [ ] `SearchPage.jsx` (Q&A interface, conversation history, category filters, and source citations)


* [ ] `AdminPage.jsx` (Document uploader, category assignment, re-indexing trigger, and CSV telemetry export)




* [ ] Wire client-side routing in `App.jsx` and styling in `App.module.css`


---

### Phase 6: Audit Validation & Testing Metrics

* [ ] **Retrieval@3 Accuracy Verification:** Validate that top-3 search chunks contain correct answers across test queries (Target: $\ge 80\%$).


* [ ] **Answer Reference Coverage Verification:** Confirm generated answers cite at least one valid source file and snippet (Target: $\ge 90\%$).


* [ ] **Response Latency Audit:** Verify auto-logged query metrics return median response time $< 3\text{s}$ and p95 $< 5\text{s}$.


* [ ] **Cache Effectiveness Test:** Perform duplicate file ingestion and repeated search queries to ensure $100\%$ cache hit rates on unchanged files.


* [ ] **Failure Handling Verification:** Test empty query strings, missing API keys, corrupted upload files, and verify clear `4xx`/`5xx` JSON error states.


* [ ] **Source Precision Check:** Spot-check snippet highlights against generated answers to confirm direct support (Target: $\ge 80\%$).