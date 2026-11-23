from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.config import AUTH_COOKIE_NAME, AUTH_COOKIE_SECURE, JWT_EXPIRE_MINUTES
from app.db import get_conn
from app.schemas import LoginRequest, MeResponse, TokenResponse
from app.security import create_access_token, current_claims, verify_password

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    response: Response,
    cookie: bool = Query(
        False,
        description="true: set the JWT in an HttpOnly cookie instead of returning it in the body",
    ),
    conn=Depends(get_conn),
):
    row = conn.execute(
        "SELECT id, email, password, salt FROM users WHERE email = %s",
        (body.email.lower(),),
    ).fetchone()
    # Same error for "no such user" and "wrong password", so emails can't be probed.
    if row is None or not verify_password(body.password, row["salt"], row["password"]):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(row["id"], row["email"])
    expires_in = JWT_EXPIRE_MINUTES * 60
    if cookie:
        response.set_cookie(
            AUTH_COOKIE_NAME,
            token,
            max_age=expires_in,
            httponly=True,  # JavaScript can't read it, so XSS can't steal it
            secure=AUTH_COOKIE_SECURE,  # HTTPS only (enable outside localhost)
            samesite="lax",  # not sent on cross-site POST/PUT/PATCH/DELETE
            path="/",
        )
        return TokenResponse(
            access_token=None,
            token_type="cookie",
            expires_in=expires_in,
            user_id=row["id"],
            email=row["email"],
        )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user_id=row["id"],
        email=row["email"],
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    """Clear the auth cookie. Only the server can, because JavaScript can't touch an
    HttpOnly cookie. (With localStorage, the client just deletes its own copy.)"""
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    resp.delete_cookie(
        AUTH_COOKIE_NAME, path="/", httponly=True, secure=AUTH_COOKIE_SECURE, samesite="lax"
    )
    return resp


@router.get("/me", response_model=MeResponse)
def me(claims: dict = Depends(current_claims), conn=Depends(get_conn)):
    """Who is logged in. Cookie-mode clients call this on page load, since they
    can't read the token to find out themselves."""
    row = conn.execute(
        "SELECT id, email FROM users WHERE id = %s", (int(claims["sub"]),)
    ).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return MeResponse(id=row["id"], email=row["email"], expires_at=claims["exp"])
