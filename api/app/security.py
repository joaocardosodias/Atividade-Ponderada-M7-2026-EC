from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from backend import database
from backend.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

ALGORITHM = "HS256"
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    target = password_hash.encode() if password_hash else _DUMMY_HASH
    try:
        matches = bcrypt.checkpw(password.encode(), target)
    except ValueError:
        return False
    return matches and password_hash is not None


def authenticate(username: str, password: str) -> dict | None:
    user = database.get_user(username)
    valid = verify_password(password, user["password_hash"] if user else None)
    return user if valid else None


def create_token(username: str) -> tuple[str, int]:
    expires_in = settings.jwt_expire_minutes * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM), expires_in


def require_user(token: str | None = Depends(oauth2_scheme)) -> str:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="token inválido, ausente ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise unauthorized
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise unauthorized from exc
    return payload["sub"]
