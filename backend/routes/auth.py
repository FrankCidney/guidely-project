from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.models.auth import UserRegister, UserLogin, TokenResponse, UserOut
from backend.services.auth_service import hash_password, verify_password, create_access_token, decode_access_token
from backend.database import get_db

router = APIRouter(prefix="/api/auth", tags=["Auth"])
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency that validates the Bearer token from the Authorization header
    and retrieves the authenticated user's record from SQLite.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    email = payload["sub"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, role, created_at FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "created_at": str(user["created_at"]) if user["created_at"] else None
    }


def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    FastAPI dependency that enforces admin role requirements on protected endpoints.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required for this action"
        )
    return current_user


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister):
    """
    Registers a new user account with the default 'reader' role.
    """
    email = user_data.email.strip().lower()
    password = user_data.password.strip()

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered"
            )

        hashed = hash_password(password)
        cursor.execute(
            "INSERT INTO users (email, hashed_password, role) VALUES (?, ?, 'reader')",
            (email, hashed)
        )
        new_id = cursor.lastrowid

        cursor.execute("SELECT id, email, role, created_at FROM users WHERE id = ?", (new_id,))
        created_user = cursor.fetchone()

    return UserOut(
        id=created_user["id"],
        email=created_user["email"],
        role=created_user["role"],
        created_at=str(created_user["created_at"]) if created_user["created_at"] else None
    )


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin):
    """
    Authenticates user credentials and returns a signed JWT access token.
    """
    email = credentials.email.strip().lower()
    password = credentials.password.strip()

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, hashed_password, role FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

    if not user or not verify_password(password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token(
        data={
            "sub": user["email"],
            "role": user["role"],
            "user_id": user["id"]
        }
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user["role"]
    )


@router.get("/me", response_model=UserOut)
def get_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Returns profile information for the currently authenticated user.
    """
    return UserOut(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
        created_at=current_user["created_at"]
    )
