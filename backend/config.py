import os
from dotenv import load_dotenv

# Load variables from root .env file
load_dotenv()

# Core AI Credentials
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Security & JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "guidely-super-secret-production-key-change-this-32-chars")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

# System Bootstrap Admin Settings
SEED_ADMIN_EMAIL = os.getenv("SEED_ADMIN_EMAIL", "admin@guidely.com")
SEED_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "admin123Password!")

# Data Paths
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "backend/data/store/guidely.db")
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "backend/data/store/faiss_index.bin")
