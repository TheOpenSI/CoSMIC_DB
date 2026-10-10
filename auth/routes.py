from urllib.parse import urlencode
from uuid import UUID

from authlib.integrations.base_client import OAuthError
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.apis.table_models.users import Users
from auth import config, keys
from auth import session as cosmic_session
from auth.claims import NormalizedClaims, keycloak_userinfo_to_claims
from auth.oauth import oauth, refresh_keycloak_token, revoke_keycloak_session
from auth.users_sync import ensure_user
from cores.db import SessionDependency

auth_router = APIRouter(prefix=config.AUTH_API_PREFIX, tags=["auth"])

_ALREADY_SIGNED_IN_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>Already signed in</title>
</head>
<body style="font-family: sans-serif; padding: 2rem;">
    <h1>Already signed in</h1>
    <p>You can close this tab and continue in the other window.</p>
    <script>
    setTimeout(function () {
        window.close();
    }, 3000);
    </script>
</body>
</html>
"""


def _keycloak_redirect(request: Request, requested: str | None = None) -> str:
    """Resolve the requested provider to the only supported login target."""
    if requested is not None and requested.strip().lower() != "keycloak":
        # Google/Microsoft are brokered inside Keycloak now; never expose a
        # direct-to-IdP path even if an old bookmark still points at one.
        return f"{config.AUTH_API_PREFIX}/login"
    return f"{config.AUTH_API_PREFIX}/login"


@auth_router.get("/providers")
async def providers() -> dict:
    """Deprecated: kept for compatibility. Keycloak is the only provider."""
    return {"enabled": ["keycloak"]}


@auth_router.get("/jwks.json")
async def jwks() -> dict:
    """Public JWKS so the other CoSMIC microservices can verify the session."""
    return keys.jwk_set()


@auth_router.get("/login")
async def login(request: Request) -> RedirectResponse:
    redirect_uri = config.callback_url("keycloak")
    return await oauth.keycloak.authorize_redirect(request, redirect_uri)


@auth_router.get("/login/{provider}")
async def login_provider(request: Request, provider: str) -> RedirectResponse:
    if provider.strip().lower() != "keycloak":
        return RedirectResponse(url=_keycloak_redirect(request, provider), status_code=302)
    redirect_uri = config.callback_url("keycloak")
    return await oauth.keycloak.authorize_redirect(request, redirect_uri)


@auth_router.get("/callback/{provider}")
async def callback_provider(
    provider: str,
    request: Request,
    session: SessionDependency,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> Response:
    if provider.strip().lower() != "keycloak":
        return RedirectResponse(url=_keycloak_redirect(request, provider), status_code=302)

    try:
        cosmic_session.read_session(request)
        # Already logged in, avoid a double callback.
        return HTMLResponse(content=_ALREADY_SIGNED_IN_HTML, status_code=200)
    except HTTPException:
        pass

    if error:
        return RedirectResponse(
            url=f"{config.FRONTEND_URL}/login?error={error}",
            status_code=302,
        )

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth code or state")

    try:
        tokens = await oauth.keycloak.authorize_access_token(
            request,
            claims_options={
                "iss": {"essential": True, "value": config.OIDC_ISSUER},
            },
        )
    except OAuthError as exc:
        raise HTTPException(
            status_code=400, detail=f"OAuth callback failed: {exc.error}"
        ) from exc

    claims = keycloak_userinfo_to_claims(tokens.get("userinfo") or {})
    user = ensure_user(session, claims)

    # Keep the id_token so logout can use RP-initiated logout.
    request.session["id_token"] = tokens.get("id_token")

    response = RedirectResponse(url=f"{config.FRONTEND_URL}/chat", status_code=302)
    refresh_max_age = tokens.get("refresh_expires_in") or config.REFRESH_COOKIE_MAX_AGE
    response.set_cookie(
        config.OAUTH_PROVIDER_COOKIE,
        "keycloak",
        max_age=refresh_max_age,
        **cosmic_session.cookie_kwargs(),
    )
    # Cosmic session (source of truth for /me)
    cosmic_session.set_session_cookie(response, claims, user.id)
    # Keep the refresh token for Keycloak session revocation on logout.
    if tokens.get("refresh_token"):
        response.set_cookie(
            config.REFRESH_TOKEN_COOKIE,
            tokens["refresh_token"],
            max_age=refresh_max_age,
            **cosmic_session.cookie_kwargs(),
        )
    # Stop treating the IdP access_token as the app session.
    response.delete_cookie(config.ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(config.OAUTH_STATE_COOKIE, path="/")
    return response


@auth_router.post("/logout")
@auth_router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    refresh_token = request.cookies.get(config.REFRESH_TOKEN_COOKIE)
    if refresh_token:
        try:
            await revoke_keycloak_session(refresh_token)
        except Exception:  # noqa: BLE001 - logout must never trap the user
            pass

    id_token = request.session.pop("id_token", None)

    params = {
        "client_id": config.KEYCLOAK_CLIENT_ID,
        "post_logout_redirect_uri": f"{config.FRONTEND_URL}/login",
    }
    if id_token:
        params["id_token_hint"] = id_token

    response = RedirectResponse(
        url=f"{config.keycloak_logout_url()}?{urlencode(params)}",
        status_code=302,
    )
    cosmic_session.clear_auth_cookies(response)
    return response


@auth_router.post("/refresh")
async def refresh(request: Request, session: SessionDependency) -> JSONResponse:
    refresh_token = request.cookies.get(config.REFRESH_TOKEN_COOKIE)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token found")

    old = cosmic_session.read_session_allowed_expired(request)
    user_id = UUID(str(old["user_id"]))
    if session.get(Users, user_id) is None:
        return cosmic_session.unauthorized_cleared()

    try:
        tokens = await refresh_keycloak_token(refresh_token)
    except Exception as exc:  # noqa: BLE001 - surface as a 401 to the client
        raise HTTPException(status_code=401, detail="Token refresh failed") from exc

    claims: NormalizedClaims | None = None
    if tokens.get("id_token"):
        try:
            userinfo = await oauth.keycloak.parse_id_token(tokens, nonce=None)
            claims = keycloak_userinfo_to_claims(userinfo)
        except Exception:  # noqa: BLE001 - fall back to the current session
            claims = None

    if claims is None or not claims.sub:
        claims = NormalizedClaims(
            provider=old.get("provider") or "keycloak",
            sub=old["sub"],
            email=old.get("email"),
            name=old.get("name"),
            roles=old.get("roles") or [],
        )

    response = JSONResponse({"ok": True})
    cosmic_session.set_session_cookie(response, claims, user_id)

    new_refresh = tokens.get("refresh_token")
    if new_refresh and new_refresh != refresh_token:
        refresh_max_age = tokens.get("refresh_expires_in") or config.REFRESH_COOKIE_MAX_AGE
        response.set_cookie(
            config.REFRESH_TOKEN_COOKIE,
            new_refresh,
            max_age=refresh_max_age,
            **cosmic_session.cookie_kwargs(),
        )
        response.set_cookie(
            config.OAUTH_PROVIDER_COOKIE,
            "keycloak",
            max_age=refresh_max_age,
            **cosmic_session.cookie_kwargs(),
        )
    return response


@auth_router.get("/me")
async def me(request: Request, session: SessionDependency) -> dict:
    payload = cosmic_session.read_session(request)
    user_id = payload.get("user_id")
    if not user_id or session.get(Users, UUID(str(user_id))) is None:
        return cosmic_session.unauthorized_cleared()
    return {
        "user_id": payload.get("user_id"),
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "roles": payload.get("roles", []),
        "provider": payload.get("provider"),
    }
