import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import (
    AUTH_COOKIE_NAME,
    CSRF_HEADER,
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    JWT_SECRET,
)

PBKDF2_ITERATIONS = 600_000  # OWASP recommendation for PBKDF2-HMAC-SHA256


def new_salt() -> str:
    return secrets.token_hex(16)


def hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return digest.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password, salt), expected_hash)


def create_access_token(user_id: int, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


bearer = HTTPBearer(auto_error=False)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_claims(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    """Dependency that requires a valid JWT, sent either way:

    - `Authorization: Bearer <jwt>` header (frontend keeps the token in localStorage)
    - the HttpOnly `access_token` cookie set by `POST /login?cookie=true`

    Browsers attach cookies to every request automatically, even ones triggered by
    another website (CSRF). So cookie-authenticated writes must also send a custom
    header: a cross-site HTML form can't set one, and CORS blocks other origins'
    scripts from sending it. Bearer tokens don't need this; browsers never add them.
    """
    if creds is not None:
        token = creds.credentials
    else:
        token = request.cookies.get(AUTH_COOKIE_NAME)
        if token and request.method not in SAFE_METHODS and not request.headers.get(CSRF_HEADER):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, f"Missing {CSRF_HEADER} header (CSRF protection)"
            )
    if not token:
        raise _unauthorized("Not authenticated")
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise _unauthorized("Invalid or expired token")


def current_user_id(claims: dict = Depends(current_claims)) -> int:
    return int(claims["sub"])
