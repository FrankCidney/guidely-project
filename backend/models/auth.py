from typing import Optional
from pydantic import BaseModel


class UserRegister(BaseModel):
    """Schema for user registration request."""
    email: str
    password: str


class UserLogin(BaseModel):
    """Schema for user login request."""
    email: str
    password: str


class TokenResponse(BaseModel):
    """Schema for successful authentication response containing JWT."""
    access_token: str
    token_type: str = "bearer"
    role: str


class UserOut(BaseModel):
    """Schema for public user profile data (excludes password)."""
    id: int
    email: str
    role: str
    created_at: Optional[str] = None
