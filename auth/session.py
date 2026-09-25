from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from uuid import UUID

from auth import config
from auth.providers.base import NormalizedClaims


def _cookie_kwargs(max_age: int | None = None) -> dict:
    secure = config.AUTH_PUBLIC_URL.startswith("https://")
    kwargs = {
        "httponly": True,
        "secure": secure,
        "samesite": "lax",
        "path": "/",
    }
    if max_age is not None:
        kwargs["max_age"] = max_age
    return kwargs


def issue_session_token(claims: NormalizedClaims,user_id: UUID) -> str:
    """Build a Cosmic JWT from normalized IdP claims."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": claims.sub,
        "email": claims.email,
        "name": claims.name,
        "roles": claims.roles,
        "provider": claims.provider,
        "user_id": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=config.SESSION_MAX_AGE),
    }
    return jwt.encode(payload, config.SESSION_SECRET, algorithm="HS256")


def set_session_cookie(response: Response, claims: NormalizedClaims,user_id: UUID) -> None:
    token = issue_session_token(claims, user_id)
    response.set_cookie(
        config.SESSION_COOKIE_NAME,
        token,
        **_cookie_kwargs(config.REFRESH_COOKIE_MAX_AGE),
    )



def read_session(request: Request) -> dict:
    """Decode + verify Cosmic session cookie. Raises 401 if missing/invalid."""
    token = request.cookies.get(config.SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        return jwt.decode(
            token,
            config.SESSION_SECRET,
            algorithms=["HS256"],
            options={"require": ["exp","iat","sub"]}
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=401, detail="Invalid or expired session"
        ) from exc

def read_session_allowed_expired(request: Request) -> dict:

    #This endpoint only for refresh token and only designed beacuse google idp dosent give access_token or any deatils not stored in refresh token so we need to get details from expired acees token.
    token = request.cookies.get(config.SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        return jwt.decode(
            token,
            config.SESSION_SECRET,
            algorithms=["HS256"],
            options={
                "require": ["exp","iat","sub"],
                "verify_exp": False}, # Allow expired tokens to be read

        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc

def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(config.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(config.ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(config.REFRESH_TOKEN_COOKIE, path="/")
    response.delete_cookie(config.OAUTH_PROVIDER_COOKIE, path="/")
    response.delete_cookie(config.OAUTH_STATE_COOKIE, path="/")


def unauthorized_cleared(detail: str = "User no longer exists") -> JSONResponse:
    response = JSONResponse(status_code=401, content={"detail": detail})
    clear_auth_cookies(response)
    return response