### Core modules ###
from urllib.parse import urlencode
from authlib.integrations.base_client import OAuthError
from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    Response,
    status
)
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse
)


### Type hints ###
from typing import Any
from uuid import UUID
from app.types.tags import APITag


### Internal modules ###
from . import (
    config,
    keys
)
from . import session as cosmic_session
from .claims import (
    NormalisedClaims,
    keycloak_userinfo_to_claims
)
from .models import Users
from .oauth import (
    oauth,
    refresh_keycloak_token,
    revoke_keycloak_session
)
from .users_sync import ensure_user
from app.cores.db import SessionDependency


auth_v1_router: APIRouter = APIRouter(
    prefix=config.AUTH_API_PREFIX,
    tags=[APITag.auth]
)


_ALREADY_SIGNED_IN_HTML: str = """
    <!DOCTYPE html>

    <html lang="en">
        <head>
            <meta charset="utf-8" />
            <title>Already signed in</title>
        </head>

        <body style="font-family: sans-serif; padding: 2rem;">
            <h1>Already signed in</h1>
            <p>You can close this tab and continue in the other window.</p>
            <script>
                setTimeout(
                    () => { window.close();},
                    3000
                );
            </script>
        </body>
    </html>
"""


def _keycloak_redirect(requested: str | None = None) -> str:
    """Resolve the requested provider to the only supported login target."""
    # NOTE:
    # Google/Microsoft are brokered inside Keycloak now. Therefore, we cannot
    # expose a direct-to-IdP path even if an old bookmark still points at one.
    return f"{config.AUTH_API_PREFIX}/login"


@auth_v1_router.get(
    path="/jwks.json",
    status_code=status.HTTP_200_OK
)
async def jwks() -> dict[str, list[dict[str, str | list[str]]]]:
    """Public JWKS so the other CoSMIC microservices can verify the session."""
    return keys.jwk_set()


@auth_v1_router.get(
    path="/login",
    status_code=status.HTTP_200_OK
)
async def login(request: Request) -> RedirectResponse:
    redirect_uri: str = config.callback_url("keycloak")

    return await oauth.keycloak.authorize_redirect(request, redirect_uri)


@auth_v1_router.get(
    path="/login/{provider}",
    status_code=status.HTTP_200_OK
)
async def login_provider(
    request: Request,
    provider: str
) -> RedirectResponse:
    if provider.strip().lower() != "keycloak":
        return RedirectResponse(
            url=_keycloak_redirect(requested=provider),
            status_code=status.HTTP_302_FOUND
        )
    redirect_uri: str = config.callback_url("keycloak")

    return await oauth.keycloak.authorize_redirect(
        request,
        redirect_uri
    )


@auth_v1_router.get(
    path="/callback/{provider}",
    status_code=status.HTTP_200_OK
)
async def callback_provider(
    provider:   str,
    request:    Request,
    session:    SessionDependency,
    code:       str | None = None,
    state:      str | None = None,
    error:      str | None = None
) -> Response:
    if provider.strip().lower() != "keycloak":
        return RedirectResponse(
            url=_keycloak_redirect(requested=provider),
            status_code=status.HTTP_302_FOUND
        )

    try:
        cosmic_session.read_session(request=request)

        # Already logged in, avoid a double callback.
        return HTMLResponse(
            content=_ALREADY_SIGNED_IN_HTML,
            status_code=status.HTTP_200_OK
        )

    except HTTPException:
        pass

    if error:
        return RedirectResponse(
            url=f"{config.FRONTEND_URL}/login?error={error}",
            status_code=status.HTTP_302_FOUND
        )

    if (
        not code
        or
        not state
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth code or state"
        )

    try:
        tokens = await oauth.keycloak.authorize_access_token(
            request,
            claims_options={
                "iss": {
                    "essential": True,
                    "value": config.OIDC_ISSUER
                }
            },
        )

    except OAuthError as oauth_exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback failed: {oauth_exc.error}"
        )

    claims: NormalisedClaims = keycloak_userinfo_to_claims(userinfo=tokens.get("userinfo") or {})
    user: Users = ensure_user(
        session=session,
        claims=claims
    )

    # Keep the id_token so logout can use RP-initiated logout.
    request.session["id_token"] = tokens.get("id_token")

    response: RedirectResponse = RedirectResponse(
        url=f"{config.FRONTEND_URL}/chat",
        status_code=status.HTTP_302_FOUND
    )

    # Cosmic session is the single source of truth for /me, /refresh and /logout.
    # The Keycloak refresh token travels inside the JWT.
    cosmic_session.set_session_cookie(
        response=response,
        claims=claims,
        user_id=user.id,
        refresh_token=tokens.get("refresh_token"),
        max_age=tokens.get("refresh_expires_in")
    )

    return response


@auth_v1_router.post(
    path="/logout",
    status_code=status.HTTP_200_OK
)
async def logout(request: Request) -> RedirectResponse:
    refresh_token: str | None = None

    try:
        old: dict[str, str | list[str] | None] = (
            cosmic_session.read_session_allowed_expired(request=request)
        )
        stored_refresh: str | list[str] | None = old.get("refresh_token")
        refresh_token = stored_refresh if isinstance(stored_refresh, str) else None

    except HTTPException:
        refresh_token = None

    if refresh_token:
        try:
            await revoke_keycloak_session(refresh_token=refresh_token)

        except Exception:  # noqa: BLE001 - logout must never trap the user
            pass

    id_token: Any = request.session.pop("id_token", None)

    params: dict[str, str | None] = {
        "client_id":                config.KEYCLOAK_CLIENT_ID,
        "post_logout_redirect_uri": f"{config.FRONTEND_URL}/login"
    }

    if id_token:
        params["id_token_hint"] = id_token

    response: RedirectResponse = RedirectResponse(
        url=f"{config.keycloak_logout_url()}?{urlencode(params)}",
        status_code=status.HTTP_302_FOUND
    )

    cosmic_session.clear_auth_cookies(response=response)

    return response


@auth_v1_router.post(
    path="/refresh",
    status_code=status.HTTP_200_OK
)
async def refresh(
    request: Request,
    session: SessionDependency
) -> JSONResponse:
    old: dict[str, str | list[str] | None] = (
        cosmic_session.read_session_allowed_expired(request=request)
    )

    stored_refresh: str | list[str] | None = old.get("refresh_token")
    refresh_token: str | None = (
        stored_refresh if isinstance(stored_refresh, str) else None
    )

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token in session"
        )

    user_id: UUID = UUID(str(old["user_id"]))

    if session.get(Users, user_id) is None:
        return cosmic_session.unauthorised_cleared()

    try:
        tokens = await refresh_keycloak_token(refresh_token=refresh_token)

    except Exception:  # noqa: BLE001 - surface as a 401 to the client
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )

    claims: NormalisedClaims | None = None

    if tokens.get("id_token"):
        try:
            userinfo: dict[str, Any] = await oauth.keycloak.parse_id_token(
                tokens,
                nonce=None
            )

            claims = keycloak_userinfo_to_claims(userinfo)

        except Exception:  # noqa: BLE001 - fall back to the current session
            claims = None

    if (
        claims is None
        or
        not claims.sub
    ):
        claims = NormalisedClaims(
            provider=old.get("provider") or "keycloak",
            sub=old["sub"],
            email=old.get("email"),
            name=old.get("name"),
            roles=old.get("roles") or [],
        )

    new_refresh: str | None = tokens.get("refresh_token") or refresh_token

    response: JSONResponse = JSONResponse({"ok": True})
    cosmic_session.set_session_cookie(
        response=response,
        claims=claims,
        user_id=user_id,
        refresh_token=new_refresh,
        max_age=tokens.get("refresh_expires_in")
    )

    return response


@auth_v1_router.get(
    path="/me",
    status_code=status.HTTP_200_OK
)
async def me(
    request: Request,
    session: SessionDependency
) -> dict[str, str | list[str] | None]:
    payload: dict[str, str | list[str] | None] = cosmic_session.read_session(request=request)
    user_id: str | list[str] | None = payload.get("user_id")

    if (
        not user_id
        or session.get(Users, UUID(str(user_id))) is None
    ):
        return cosmic_session.unauthorised_cleared()

    return {
        "user_id":  payload.get("user_id"),
        "sub":      payload.get("sub"),
        "email":    payload.get("email"),
        "name":     payload.get("name"),
        "roles":    payload.get("roles", []),
        "provider": payload.get("provider")
    }
