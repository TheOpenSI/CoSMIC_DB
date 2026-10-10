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
from .config import (
    FRONTEND_URL,
    KEYCLOAK_CLIENT_ID,
    OIDC_ISSUER,
    callback_url,
    keycloak_logout_url
)
from .keys import jwk_set
from .session import (
    clear_auth_cookies,
    read_current_session,
    read_expired_session,
    set_session_cookie,
    unauthorised_cleared
)
from .claims import (
    NormalisedClaims,
    keycloak_user_info_to_claims
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
    prefix="/api/v1/auth",
    tags=[APITag.auth]
)


_ALREADY_SIGNED_IN_TEMPLATE: str = """
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
                    3000,
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
    return "/api/v1/auth/login"


@auth_v1_router.get(
    path="/jwks.json",
    status_code=status.HTTP_200_OK
)
async def jwks() -> dict[str, list[dict[str, str | list[str]]]]:
    """Public JWKS so the other CoSMIC microservices can verify the session."""
    return jwk_set()


@auth_v1_router.get(
    path="/login",
    status_code=status.HTTP_200_OK
)
async def login(request: Request) -> RedirectResponse:
    redirect_uri: str = callback_url(provider="keycloak")

    return await oauth.keycloak.authorize_redirect(
        request,
        redirect_uri
    )


@auth_v1_router.get(
    path="/login/{provider}",
    status_code=status.HTTP_200_OK
)
async def login_provider(
    request:    Request,
    provider:   str
) -> RedirectResponse:
    if provider.strip().lower() != "keycloak":
        return RedirectResponse(
            url=_keycloak_redirect(requested=provider),
            status_code=status.HTTP_302_FOUND
        )

    redirect_uri: str = callback_url(provider="keycloak")

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
        read_current_session(request=request)

        # Already logged in, avoid a double callback.
        return HTMLResponse(
            content=_ALREADY_SIGNED_IN_TEMPLATE,
            status_code=status.HTTP_200_OK
        )

    except HTTPException:
        pass

    if error:
        return RedirectResponse(
            url=f"{str(FRONTEND_URL)}/login?error={error}",
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
                    "value": str(OIDC_ISSUER)
                }
            },
        )

        claims: NormalisedClaims = keycloak_user_info_to_claims(
            user_info=tokens.get(
                "userinfo",
                {}
            )
        )

        user: Users = ensure_user(
            session=session,
            claims=claims
        )

        # Keep the ID token so logout can use RP-initiated logout.
        request.session["id_token"] = tokens.get(
            "id_token",
            None
        )

        response: RedirectResponse = RedirectResponse(
            url=f"{str(FRONTEND_URL)}/chat",
            status_code=status.HTTP_302_FOUND
        )

        # CoSMIC session is the single source of truth for `/me`, `/refresh` &
        # `/logout` endpoints. The Keycloak refresh token travels inside the JWT
        # token
        set_session_cookie(
            response=response,
            claims=claims,
            user_id=user.id,
            refresh_token=tokens.get(
                "refresh_token",
                None
            ),
            max_age=tokens.get(
                "refresh_expires_in",
                None
            )
        )

        return response

    except OAuthError as oauth_exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "400 - Bad Request",
                "message": f"OAuth callback failed: {oauth_exc.error}."
            }
        )


@auth_v1_router.post(
    path="/logout",
    status_code=status.HTTP_200_OK
)
async def logout(request: Request) -> RedirectResponse:
    refresh_token: str | None = None

    try:
        old_session_token: dict[str, str | list[str] | None] = read_expired_session(request=request)
        stored_refresh_token: str | list[str] | None = old_session_token.get(
            "refresh_token",
            None
        )
        refresh_token: str | list[str] | None = (
            stored_refresh_token
            if   (isinstance(stored_refresh_token, str))
            else (None)
        )

    except HTTPException as fastapi_exc:
        refresh_token = None

    if refresh_token:
        try:
            await revoke_keycloak_session(refresh_token=refresh_token)

        except Exception:  # noqa: BLE001 - logout must never trap the user
            pass

    id_token: str | None = request.session.pop(
        "id_token",
        None
    )

    params: dict[str, str | None] = {
        "client_id":                str(KEYCLOAK_CLIENT_ID),
        "post_logout_redirect_uri": f"{str(FRONTEND_URL)}/login"
    }

    if id_token:
        params["id_token_hint"] = id_token

    response: RedirectResponse = RedirectResponse(
        url=f"{keycloak_logout_url()}?{urlencode(query=params)}",
        status_code=status.HTTP_302_FOUND
    )

    clear_auth_cookies(response=response)

    return response


@auth_v1_router.post(
    path="/refresh",
    status_code=status.HTTP_200_OK
)
async def refresh(
    request: Request,
    session: SessionDependency
) -> JSONResponse:
    old_session_token: dict[str, str | list[str] | None] = read_expired_session(request=request)
    stored_refresh_token: str | list[str] | None = old_session_token.get(
        "refresh_token",
        None
    )
    refresh_token: str | list[str] | None = (
        stored_refresh_token
        if   (isinstance(stored_refresh_token, str))
        else (None)
    )

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "401 - Unauthorized",
                "message": "No refresh token in session."
            }
        )

    user_id: UUID = UUID(str(old_session_token["user_id"]))

    if session.get(
        entity=Users,
        ident=user_id
    ) is None:
        return unauthorised_cleared()

    try:
        tokens: dict[str, str]          = await refresh_keycloak_token(refresh_token=refresh_token)
        claims: NormalisedClaims | None = None

        if tokens.get(
            "id_token",
            None
        ):
            try:
                user_info: dict[str, Any] = await oauth.keycloak.parse_id_token(
                    tokens,
                    nonce=None
                )

                claims = keycloak_user_info_to_claims(user_info=user_info)

            except Exception:  # noqa: BLE001 - fall back to the current session
                claims = None

        if (
            claims is None
            or
            not claims.sub
        ):
            claims = NormalisedClaims(
                provider=old_session_token.get(
                    "provider",
                    "keycloak"
                ),
                sub=old_session_token.get(
                    "sub",
                    None
                ),
                email=old_session_token.get(
                    "email",
                    None
                ),
                name=old_session_token.get(
                    "name",
                    None
                ),
                roles=old_session_token.get(
                    "roles",
                    []
                )
            )

        new_refresh: str | None = tokens.get(
            "refresh_token",
            refresh_token
        )

        set_session_cookie(
            response=JSONResponse({"ok": True}),
            claims=claims,
            user_id=user_id,
            refresh_token=new_refresh,
            max_age=tokens.get(
                "refresh_expires_in",
                None
            )
        )

        return JSONResponse({"ok": True})

    except Exception:  # noqa: BLE001 - surface as a 401 to the client
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "401 - Unauthorized",
                "message": "Token refresh failed."
            }
        )


@auth_v1_router.get(
    path="/me",
    status_code=status.HTTP_200_OK
)
async def me(
    request: Request,
    session: SessionDependency
) -> JSONResponse:
    payload: dict[str, str | list[str] | None] = read_current_session(request=request)
    user_id: str | list[str] | None = payload.get(
        "user_id",
        None
    )

    if (
        not user_id
        or session.get(
            entity=Users,
            ident=UUID(str(user_id))
        ) is None
    ):
        return unauthorised_cleared()

    return JSONResponse(
        {
            "user_id": payload.get(
                "user_id",
                None
            ),
            "sub": payload.get(
                "sub",
                None
            ),
            "email": payload.get(
                "email",
                None
            ),
            "name": payload.get(
                "name",
                None
            ),
            "roles": payload.get(
                "roles",
                []
            ),
            "provider": payload.get(
                "provider",
                None
            )
        }
    )
