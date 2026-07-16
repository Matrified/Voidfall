"""Authentication: password hashing and JWT issuing/verification.

Passwords are hashed with bcrypt and never stored in plaintext. Tokens are short-lived
HS256 JWTs scoped to a user id. The ``current_user`` dependency rejects any request that
lacks a valid, unexpired token or belongs to a disabled account.
"""

from __future__ import annotations

import datetime as dt

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .db import User, get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

# --- password policy ------------------------------------------------------

MIN_PASSWORD = 12
MAX_PASSWORD = 128


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def password_policy_error(password: str) -> str | None:
    """Return a message if the password fails policy, else ``None``."""
    if not MIN_PASSWORD <= len(password) <= MAX_PASSWORD:
        return f"Password must be {MIN_PASSWORD}-{MAX_PASSWORD} characters."
    checks = (
        (any(c.islower() for c in password), "a lowercase letter"),
        (any(c.isupper() for c in password), "an uppercase letter"),
        (any(c.isdigit() for c in password), "a digit"),
        (any(not c.isalnum() for c in password), "a symbol"),
    )
    missing = [label for ok, label in checks if not ok]
    return "Password must contain " + ", ".join(missing) + "." if missing else None


# --- tokens ---------------------------------------------------------------


def create_access_token(user_id: int, settings: Settings) -> str:
    now = dt.datetime.now(dt.UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + dt.timedelta(seconds=settings.jwt_ttl_seconds),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise credentials_error from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
