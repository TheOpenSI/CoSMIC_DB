"""
OAuth2/OIDC client registry for the CoSMIC Auth BFF framework.


Only Keycloak is registered since Google & Microsoft are brokered *inside*
Keycloak (see ``docker/keycloak/cosmic-realm.json``). This way, the BFF framework
always talks to a single OpenID Connect provider and runs a single
authorisation-code flow.

One important note is that the browser must be sent to ``KEYCLOAK_PUBLIC_URL``
while the container exchanges the code and fetches JWKS from
``KEYCLOAK_INTERNAL_URL``. We therefore register the endpoints explicitly instead
of relying on OIDC discovery, whose ``token_endpoint``/``jwks_uri`` would resolve
to a browser-only host from inside the container.
"""


### Core modules ###
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.integrations.starlette_client import OAuth


### Type hints ###


### Internal modules ###
from .config import (
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_CLIENT_SECRET,
    keycloak_authorise_url,
    keycloak_jwks_url,
    keycloak_logout_url,
    keycloak_token_url
)


oauth: OAuth = OAuth()


oauth.register(
    name="keycloak",
    client_id=str(KEYCLOAK_CLIENT_ID),
    client_secret=str(KEYCLOAK_CLIENT_SECRET),
    authorize_url=keycloak_authorise_url(),
    access_token_url=keycloak_token_url(),
    jwks_uri=keycloak_jwks_url(),
    client_kwargs={"scope": "openid profile email"}
)


async def refresh_keycloak_token(refresh_token: str) -> dict[str, str]:
    """Exchange a refresh token at Keycloak without a metadata round-trip."""
    async with AsyncOAuth2Client( # pyright: ignore[reportGeneralTypeIssues]
        client_id=str(KEYCLOAK_CLIENT_ID),
        client_secret=str(KEYCLOAK_CLIENT_SECRET)
    ) as client:
        return await client.refresh_token(
            keycloak_token_url(),
            refresh_token=refresh_token
        )


async def revoke_keycloak_session(refresh_token: str) -> None:
    """Best-effort to end the Keycloak session tied to this refresh token."""
    async with AsyncOAuth2Client( # pyright: ignore[reportGeneralTypeIssues]
        client_id=str(KEYCLOAK_CLIENT_ID),
        client_secret=str(KEYCLOAK_CLIENT_SECRET)
    ) as client:
        await client.post(
            keycloak_logout_url(),
            data={
                "client_id":        str(KEYCLOAK_CLIENT_ID),
                "client_secret":    str(KEYCLOAK_CLIENT_SECRET),
                "refresh_token":    refresh_token
            },
        )

        return None
