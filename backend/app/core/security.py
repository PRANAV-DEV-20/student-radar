import re
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

import bcrypt
from jose import jwt, JWTError

from app.core.config import settings

# bcrypt only considers the first 72 bytes of a password. Rejecting longer
# passwords explicitly avoids silent truncation and keeps us compatible with
# bcrypt >= 4.1 / 5.x (which raises instead of truncating).
BCRYPT_MAX_BYTES = 72


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Returns ``False`` for malformed hashes instead of raising, so invalid /
    legacy values in the database can never turn a login into a 500 error.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    """Hash a password with bcrypt, enforcing the 72-byte input limit."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_BYTES:
        raise ValueError("Password must be at most 72 bytes long.")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Decode a JWT and return its subject, or ``None`` for invalid tokens."""
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        return None

    subject = payload.get("sub")
    return str(subject) if subject is not None else None


def compute_sha256(text: str) -> str:
    """Computes a lowercased hex SHA-256 digest of normalized text."""
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def is_valid_sha256(hash_str: str) -> bool:
    """Validates that a string is a 64-character lowercase hex string."""
    return bool(isinstance(hash_str, str) and re.fullmatch(r"[a-f0-9]{64}", hash_str))
