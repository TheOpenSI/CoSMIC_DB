from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwt import JWTClaimsRegistry

from auth import config, keys
from auth.claims import NormalizedClaims


def cookie_kwargs(max_age: int | None = None) -> dict:
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


def issue_session_token(claims: NormalizedClaims, user_id: UUID) -> str:
    """Build a Cosmic session JWT (RS256) from normalized IdP claims."""
    now = datetime.now(timezone.utc)
    payload = {
        "iss": config.SESSION_ISSUER,
        "sub": claims.sub,
        "email": claims.email,
        "name": claims.name,
        "roles": claims.roles,
        "provider": claims.provider,
        "user_id": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=config.SESSION_MAX_AGE),
    }
    header = {"alg": "RS256", "typ": "JWT", "kid": keys.key_id()}
    return jwt.encode(header, payload, keys.private_key())


def set_session_cookie(response: Response, claims: NormalizedClaims, user_id: UUID) -> None:
    token = issue_session_token(claims, user_id)
    response.set_cookie(
        config.SESSION_COOKIE_NAME,
        token,
        **cookie_kwargs(config.REFRESH_COOKIE_MAX_AGE),
    )


def _claims_registry() -> JWTClaimsRegistry:
    return JWTClaimsRegistry(
        iss={"essential": True, "value": config.SESSION_ISSUER},
        sub={"essential": True},
        iat={"essential": True},
        exp={"essential": True},
    )


def _read_token_claims(request: Request, verify_exp: bool) -> dict:
    token = request.cookies.get(config.SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        obj = jwt.decode(token, keys.public_key(), algorithms=["RS256"])
    except JoseError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc

    claims = dict(obj.claims)
    if not claims.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid session")

    if verify_exp:
        try:
            _claims_registry().validate(claims)
        except JoseError as exc:
            raise HTTPException(
                status_code=401, detail="Invalid or expired session"
            ) from exc
    return claims


def read_session(request: Request) -> dict:
    """Decode + verify the Cosmic session cookie. Raises 401 if missing/invalid."""
    return _read_token_claims(request, verify_exp=True)


def read_session_allowed_expired(request: Request) -> dict:
    """Read the session even when the access token has expired.

    Only used by ``POST /refresh``: Google-style IdPs omit identity details from
    the refresh response, so the (signature-verified) expired session is the
    only place those claims are still available.
    """
    return _read_token_claims(request, verify_exp=False)


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(config.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(config.ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(config.REFRESH_TOKEN_COOKIE, path="/")
    response.delete_cookie(config.OAUTH_PROVIDER_COOKIE, path="/")
    response.delete_cookie(config.OAUTH_STATE_COOKIE, path="/")
    response.delete_cookie(config.OAUTH_SESSION_COOKIE, path="/")


def unauthorized_cleared(detail: str = "User no longer exists") -> JSONResponse:
    response = JSONResponse(status_code=401, content={"detail": detail})
    clear_auth_cookies(response)
    return response
