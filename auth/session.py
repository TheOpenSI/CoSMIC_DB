### Core modules ###
from datetime import (
    datetime,
    timedelta,
    timezone
)
from fastapi import (
    HTTPException,
    Request,
    Response,
    status
)
from fastapi.responses import JSONResponse
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwt import (
    JWTClaimsRegistry,
    Token
)


### Type hints ###
from pydantic.types import UUID7


### Internal modules ###
from .config import (
    AUTH_PUBLIC_URL,
    SESSION_COOKIE_NAME,
    SESSION_ISSUER,
    SESSION_MAX_AGE,
    SESSION_OAUTH_COOKIE,
    SESSION_REFRESH_TOKEN_MAX_AGE
)
from .keys import (
    key_id,
    private_key,
    public_key
)
from .claims import NormalisedClaims


def issue_session_token(
    claims:         NormalisedClaims,
    user_id:        UUID7,
    refresh_token:  str | None = None
) -> str:
    """
    Build a Cosmic session JWT (RS256) from normalised IdP claims.

    The Keycloak refresh token rides along as a claim so the whole session is a
    single HttpOnly cookie. `/refresh` and `/logout` endpoints read the (possibly
    expired) JWT token and pull the refresh token back out of it.
    """
    now: datetime = datetime.now(tz=timezone.utc)

    payload: dict[str, str | list[str] | datetime | None] = {
        "iss":           str(SESSION_ISSUER),
        "sub":           claims.sub,
        "email":         claims.email,
        "name":          claims.name,
        "roles":         claims.roles,
        "provider":      claims.provider,
        "user_id":       str(user_id),
        "refresh_token": refresh_token,
        "iat":           now,
        "exp":           now + timedelta(seconds=int(SESSION_MAX_AGE))
    }

    header: dict[str, str] = {
        "alg": "RS256",
        "typ": "JWT",
        "kid": key_id()
    }

    return jwt.encode(
        header=header,
        claims=payload,
        key=private_key()
    )


def set_session_cookie(
    response:       Response,
    claims:         NormalisedClaims,
    user_id:        UUID7,
    refresh_token:  str | None = None,
    max_age:        int | None = None
) -> None:
    """
    Set the CoSMIC session cookie.

    ``max_age`` should be the IdP refresh-token lifespan so the (expired) JWT is
    still delivered to `/refresh` endpoint. It defaults to the configured refresh
    window.
    """
    token: str = issue_session_token(
        claims=claims,
        user_id=user_id,
        refresh_token=refresh_token
    )

    response.set_cookie(
        key=str(SESSION_COOKIE_NAME),
        value=token,
        max_age=(
            max_age
            or
            int(SESSION_REFRESH_TOKEN_MAX_AGE)
        ),
        path="/",
        secure=str(AUTH_PUBLIC_URL).startswith("https://"),
        httponly=True,
        samesite="lax"
    )


def _claims_registry() -> JWTClaimsRegistry:
    return JWTClaimsRegistry(
        iss={
            "essential": True,
            "value": str(SESSION_ISSUER)
        },
        sub={"essential": True},
        iat={"essential": True},
        exp={"essential": True},
    )


def _read_token_claims(
    request:    Request,
    verify_exp: bool
) -> dict[str, str | list[str] | None]:
    token: str | None = request.cookies.get(
        str(SESSION_COOKIE_NAME),
        None
    )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "401 - Unauthorized",
                "message": "Not authenticated."
            }
        )

    try:
        obj: Token = jwt.decode(
            value=token,
            key=public_key(),
            algorithms=["RS256"]
        )

    except JoseError as jwt_exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "401 - Unauthorized",
                "message": "Invalid or expired session."
            }
        ) from jwt_exc

    claims: dict[str, str | list[str] | None] = dict(obj.claims)

    if not claims.get(
        "sub",
        None
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "401 - Unauthorized",
                "message": "Invalid session."
            }
        )

    if verify_exp:
        try:
            _claims_registry().validate(claims)

        except JoseError as jwt_exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "status": "401 - Unauthorized",
                    "message": "Invalid or expired session."
                }
            ) from jwt_exc

    return claims


def read_current_session(request: Request) -> dict[str, str | list[str] | None]:
    """Decode + verify the CoSMIC session cookie. Raises 401 if missing/invalid."""
    return _read_token_claims(
        request=request,
        verify_exp=True
    )


def read_expired_session(request: Request) -> dict[str, str | list[str] | None]:
    """
    Read the session even when the access token has expired.

    Only used by ``POST /refresh`` and ``POST /logout`` endpoint as the signature
    is still verified, but the expired JWT token is the only place the Keycloak
    refresh token is still available.
    """
    return _read_token_claims(
        request=request,
        verify_exp=False
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=str(SESSION_COOKIE_NAME),
        path="/"
    )
    response.delete_cookie(
        key=str(SESSION_OAUTH_COOKIE),
        path="/"
    )


def unauthorised_cleared(detail: str = "User no longer exists") -> JSONResponse:
    response: JSONResponse = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": detail}
    )

    clear_auth_cookies(response=response)

    return response
