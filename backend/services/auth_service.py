from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from backend.config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
import bcrypt

def hash_password(password: str) -> str:
    """
    Takes a plain text password and returns a salted bcrypt hash.
    Example output: '$2b$12$e8uq...xyz'
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies that a plain text password matches a stored bcrypt hash.
    Returns True if valid, False otherwise.
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a signed JSON Web Token (JWT) containing user identity and role claims.
    
    Parameters:
      - data: Dictionary containing payload claims (e.g. {'sub': 'user@example.com', 'role': 'reader'})
      - expires_delta: Optional custom token lifetime. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

        
def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodes and verifies a JWT token using our secret key and algorithm.
    Returns the decoded dictionary payload if valid, or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None