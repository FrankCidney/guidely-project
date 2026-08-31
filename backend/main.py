import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from backend.config import SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD
from backend.database import init_db, get_db
from backend.services.auth_service import hash_password
from backend.routes.auth import router as auth_router
from backend.routes.documents import router as documents_router, get_vector_store
from backend.routes.search import router as search_router
from backend.routes.system import router as system_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("guidely")


def seed_admin_user():
    """
    Auto-seeds the default administrator account on application startup
    if an account with SEED_ADMIN_EMAIL does not already exist.
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email FROM users WHERE email = ?", (SEED_ADMIN_EMAIL,))
            existing = cursor.fetchone()

            if not existing:
                hashed = hash_password(SEED_ADMIN_PASSWORD)
                cursor.execute(
                    "INSERT INTO users (email, hashed_password, role) VALUES (?, ?, 'admin')",
                    (SEED_ADMIN_EMAIL, hashed)
                )
                logger.info(f"Auto-seeded default admin user: {SEED_ADMIN_EMAIL}")
            else:
                logger.info(f"Admin user already exists: {SEED_ADMIN_EMAIL}")
    except Exception as e:
        logger.error(f"Failed to seed admin user on startup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan context manager:
      - Runs on server startup: initializes SQLite tables, seeds default admin, loads FAISS index.
      - Runs on server shutdown: cleanup operations.
    """
    logger.info("Initializing Guidely backend...")
    init_db()
    seed_admin_user()
    vstore = get_vector_store()
    logger.info(f"FAISS Vector Store ready. Total indexed vectors: {vstore.total_vectors}")
    yield
    logger.info("Shutting down Guidely backend...")


# Initialize FastAPI application
app = FastAPI(
    title="Guidely API",
    description="Internal Knowledge Q&A Assistant (RAG Pipeline)",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for Frontend integration (Vite dev server & production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handlers for standard 4xx / 5xx error JSON formats
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "detail": exc.detail
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_msg = errors[0].get("msg", "Invalid request body") if errors else "Validation error"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "status_code": 422,
            "detail": f"Validation Error: {first_msg}",
            "errors": errors
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "status_code": 500,
            "detail": "An internal server error occurred"
        }
    )


# Mount API Routers
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(system_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
