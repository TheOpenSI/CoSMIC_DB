"""Authlib OAuth2/OIDC client registry for the CoSMIC Auth BFF.

Only Keycloak is registered: Google & Microsoft are brokered *inside* Keycloak
(see ``docker/keycloak/cosmic-realm.json``), so the BFF always talks to a single
OpenID Connect provider and runs a single authorization-code flow.

Split-horizon note:
    The browser must be sent to ``KEYCLOAK_PUBLIC_URL`` while the container
    exchanges the code and fetches JWKS from ``KEYCLOAK_INTERNAL_URL``. We
    therefore register the endpoints explicitly instead of relying on OIDC
    discovery, whose ``token_endpoint``/``jwks_uri`` would resolve to a
    browser-only host from inside the container.
"""

from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.integrations.starlette_client import OAuth

from auth import config

oauth = OAuth()

oauth.register(
    name="keycloak",
    client_id=config.KEYCLOAK_CLIENT_ID,
    client_secret=config.KEYCLOAK_CLIENT_SECRET,
    authorize_url=config.keycloak_authorize_url(),
    access_token_url=config.keycloak_token_url(),
    jwks_uri=config.keycloak_jwks_url(),
    client_kwargs={"scope": "openid profile email"},
)


async def refresh_keycloak_token(refresh_token: str) -> dict:
    """Exchange a refresh token at Keycloak without a metadata round-trip."""
    async with AsyncOAuth2Client(
        client_id=config.KEYCLOAK_CLIENT_ID,
        client_secret=config.KEYCLOAK_CLIENT_SECRET,
    ) as client:
        return await client.refresh_token(
            config.keycloak_token_url(), refresh_token=refresh_token
        )


async def revoke_keycloak_session(refresh_token: str) -> None:
    """Best-effort: end the Keycloak session tied to this refresh token."""
    async with AsyncOAuth2Client(
        client_id=config.KEYCLOAK_CLIENT_ID,
        client_secret=config.KEYCLOAK_CLIENT_SECRET,
    ) as client:
        await client.post(
            config.keycloak_logout_url(),
            data={
                "client_id": config.KEYCLOAK_CLIENT_ID,
                "client_secret": config.KEYCLOAK_CLIENT_SECRET,
                "refresh_token": refresh_token,
            },
        )
