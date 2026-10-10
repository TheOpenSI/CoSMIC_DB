### Core modules ###
from datetime import (
    datetime,
    timedelta,
    timezone
)
from fastapi import (
    HTTPException,
    Request,
    Response
)
from fastapi.responses import JSONResponse
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwt import JWTClaimsRegistry, Token


### Type hints ###
from pydantic.types import UUID7


### Internal modules ###
from . import (
    config,
    keys
)
from .claims import NormalisedClaims


def cookie_kwargs(max_age: int | None = None) -> dict[str, bool | str | int]:
    secure: bool = config.AUTH_PUBLIC_URL.startswith("https://")

    kwargs: dict[str, bool | str | int] = {
        "httponly": True,
        "secure": secure,
        "samesite": "lax",
        "path": "/",
    }

    if max_age is not None:
        kwargs["max_age"] = max_age

    return kwargs


def issue_session_token(
    claims: NormalisedClaims,
    user_id: UUID7,
    refresh_token: str | None = None
) -> str:
    """
    Build a Cosmic session JWT (RS256) from normalized IdP claims.

    The Keycloak refresh token rides along as a claim so the whole session is a
    single HttpOnly cookie: `/refresh` and `/logout` read the (possibly expired)
    JWT and pull the refresh token back out of it.
    """
    now: datetime = datetime.now(timezone.utc)

    payload: dict[str, str | list[str] | datetime | None] = {
        "iss":           config.SESSION_ISSUER,
        "sub":           claims.sub,
        "email":         claims.email,
        "name":          claims.name,
        "roles":         claims.roles,
        "provider":      claims.provider,
        "user_id":       str(user_id),
        "refresh_token": refresh_token,
        "iat":           now,
        "exp":           now + timedelta(seconds=config.SESSION_MAX_AGE)
    }

    header: dict[str, str] = {
        "alg": "RS256",
        "typ": "JWT",
        "kid": keys.key_id()
    }

    return jwt.encode(
        header=header,
        claims=payload,
        key=keys.private_key()
    )


def set_session_cookie(
    response: Response,
    claims: NormalisedClaims,
    user_id: UUID7,
    refresh_token: str | None = None,
    max_age: int | None = None
) -> None:
    """
    Set the single Cosmic session cookie.

    ``max_age`` should be the IdP refresh-token lifespan so the (expired) JWT is
    still delivered to `/refresh`. It defaults to the configured refresh window.
    """
    token: str = issue_session_token(
        claims=claims,
        user_id=user_id,
        refresh_token=refresh_token
    )

    response.set_cookie(
        config.SESSION_COOKIE_NAME,
        token,
        **cookie_kwargs(max_age or config.REFRESH_TOKEN_MAX_AGE),
    )


def _claims_registry() -> JWTClaimsRegistry:
    return JWTClaimsRegistry(
        iss={
            "essential": True,
            "value": config.SESSION_ISSUER
        },
        sub={"essential": True},
        iat={"essential": True},
        exp={"essential": True},
    )


def _read_token_claims(
    request: Request,
    verify_exp: bool
) -> dict[str, str | list[str] | None]:
    token: str | None = request.cookies.get(config.SESSION_COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    try:
        obj: Token = jwt.decode(
            token,
            keys.public_key(),
            algorithms=["RS256"]
        )

    except JoseError as jwt_exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session"
        ) from jwt_exc

    claims: dict[str, str | list[str] | None] = dict(obj.claims)

    if not claims.get("sub"):
        raise HTTPException(
            status_code=401,
            detail="Invalid session"
        )

    if verify_exp:
        try:
            _claims_registry().validate(claims)

        except JoseError as jwt_exc:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session"
            ) from jwt_exc

    return claims


def read_session(request: Request) -> dict[str, str | list[str] | None]:
    """Decode + verify the Cosmic session cookie. Raises 401 if missing/invalid."""
    return _read_token_claims(
        request=request,
        verify_exp=True
    )


def read_session_allowed_expired(request: Request) -> dict[str, str | list[str] | None]:
    """
    Read the session even when the access token has expired.

    Only used by ``POST /refresh`` and ``POST /logout``: the signature is still
    verified, but the expired JWT is the only place the Keycloak refresh token
    is still available.
    """
    return _read_token_claims(
        request=request,
        verify_exp=False
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=config.SESSION_COOKIE_NAME,
        path="/"
    )
    response.delete_cookie(
        key=config.OAUTH_SESSION_COOKIE,
        path="/"
    )


def unauthorised_cleared(detail: str = "User no longer exists") -> JSONResponse:
    response: JSONResponse = JSONResponse(
        status_code=401,
        content={"detail": detail}
    )

    clear_auth_cookies(response=response)

    return response
