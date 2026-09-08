import secrets


from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse,HTMLResponse
from cores.db import SessionDependency
from auth.users_sync import ensure_user

from auth import config
from auth.providers import get_provider, list_enabled_providers
from auth import session as cosmic_session

auth_router = APIRouter(prefix=config.AUTH_API_PREFIX, tags=["auth"])


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


@auth_router.get("/providers")
async def providers() -> dict:
    return {"enabled": list_enabled_providers()}


@auth_router.get("/login/{provider}")
async def login_provider(provider: str) -> RedirectResponse:
    idp = get_provider(provider)
    state = secrets.token_urlsafe(32)
    redirect_uri = config.callback_url(provider)

    response = RedirectResponse(
        url=idp.authorize_url(state, redirect_uri),
        status_code=302,
    )
    response.set_cookie(
        config.OAUTH_STATE_COOKIE, state, max_age=600, **_cookie_kwargs()
    )
    response.set_cookie(
        config.OAUTH_PROVIDER_COOKIE, provider, max_age=600, **_cookie_kwargs()
    )
    return response


@auth_router.get("/callback/{provider}")
async def callback_provider(
    provider: str,
    request: Request,
    session: SessionDependency,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:

    try:
        cosmic_session.read_session(request)
        # Already logged in to avoid double callback 
        return HTMLResponse(
            content="""<!doctype html>
    <html><body style="font-family:sans-serif;padding:2rem">
    <h1>Already signed in</h1>
    <p>You can close this tab and continue in the other window.</p>
    <script>window.close();</script>
    </body></html>""",
            status_code=200,
        )
    except HTTPException:
        pass


    if error:
        return RedirectResponse(
            url=f"{config.FRONTEND_URL}/login?error={error}",
            status_code=302,
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth code or state")

    saved_state = request.cookies.get(config.OAUTH_STATE_COOKIE)
    if not saved_state or saved_state != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    idp = get_provider(provider)
    redirect_uri = config.callback_url(provider)
    tokens = await idp.exchange_code(code, redirect_uri)
    claims = idp.normalize_claims(tokens)
    user = ensure_user(session, claims)
    response = RedirectResponse(url=f"{config.FRONTEND_URL}/chat", status_code=302)
    response.delete_cookie(config.OAUTH_STATE_COOKIE, path="/")
    # keep provider cookie for logout routing (or re-set it below)
    response.set_cookie(
        config.OAUTH_PROVIDER_COOKIE,
        provider,
        max_age=config.SESSION_MAX_AGE,
        **_cookie_kwargs(),
    )
    # ★ Cosmic session (source of truth for /me)
    cosmic_session.set_session_cookie(response, claims, user.id)
    # Optional: keep refresh token for Keycloak revoke on logout
    if tokens.refresh_token:
        response.set_cookie(
            config.REFRESH_TOKEN_COOKIE,
            tokens.refresh_token,
            max_age=tokens.refresh_expires_in or 1800,
            **_cookie_kwargs(),
        )
    # Stop treating IdP access_token as the app session (Phase 1)
    response.delete_cookie(config.ACCESS_TOKEN_COOKIE, path="/")
    return response

@auth_router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    refresh_token = request.cookies.get(config.REFRESH_TOKEN_COOKIE)
    provider_name = request.cookies.get(config.OAUTH_PROVIDER_COOKIE, "keycloak")
    try:
        idp = get_provider(provider_name)
        await idp.logout(refresh_token)
    except HTTPException:
        pass

    response = RedirectResponse(url=f"{config.FRONTEND_URL}/login", status_code=302)
    cosmic_session.clear_session_cookie(response)
    response.delete_cookie(config.ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(config.REFRESH_TOKEN_COOKIE, path="/")
    response.delete_cookie(config.OAUTH_PROVIDER_COOKIE, path="/")
    response.delete_cookie(config.OAUTH_STATE_COOKIE, path="/")
    return response


@auth_router.get("/me")
async def me(request: Request) -> dict:
    payload = cosmic_session.read_session(request)
    return {
        "user_id": payload.get("user_id"),
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "roles": payload.get("roles", []),
        "provider": payload.get("provider"),
    }