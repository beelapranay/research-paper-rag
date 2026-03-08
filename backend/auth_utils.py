from datetime import datetime, timedelta
import secrets

from jose import jwt
from passlib.context import CryptContext

from backend.config import JWT_SECRET, JWT_EXPIRE_MINUTES

# Use PBKDF2 to avoid bcrypt backend/version issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_verification_token() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
