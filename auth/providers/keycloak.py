from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException
from jwt import PyJWKClient

from auth import config
from auth.providers.base import NormalizedClaims, TokenBundle

_jwks_client: PyJWKClient | None = None


def _get_jwks() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(
            f"{config.KEYCLOAK_INTERNAL_URL}/realms/{config.KEYCLOAK_REALM}"
            "/protocol/openid-connect/certs"
        )
    return _jwks_client


class KeycloakProvider:
    name = "keycloak"

    def authorize_url(self, state: str, redirect_uri: str) -> str:
        if not config.KEYCLOAK_PUBLIC_URL:
            raise ValueError( status_code=500, detail="KEYCLOAK_PUBLIC_URL is not set")
        params = {
            "client_id": config.KEYCLOAK_CLIENT_ID,
            "response_type": "code",
            "scope": "openid profile email",
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return (
            f"{config.KEYCLOAK_PUBLIC_URL}/realms/{config.KEYCLOAK_REALM}"
            f"/protocol/openid-connect/auth?{urlencode(params)}"
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenBundle:
        token_url = (
            f"{config.KEYCLOAK_INTERNAL_URL}/realms/{config.KEYCLOAK_REALM}"
            "/protocol/openid-connect/token"
        )
        data = {
            "grant_type": "authorization_code",
            "client_id": config.KEYCLOAK_CLIENT_ID,
            "client_secret": config.KEYCLOAK_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(token_url, data=data)

        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Keycloak token exchange failed: {resp.text}",
            )

        payload = resp.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise HTTPException(status_code=502, detail="No access token returned")

        return TokenBundle(
            access_token=access_token,
            refresh_token=payload.get("refresh_token"),
            id_token=payload.get("id_token"),
            expires_in=payload.get("expires_in", 300),
            refresh_expires_in=payload.get("refresh_expires_in"),
            raw=payload,
        )

    def normalize_claims(self, tokens: TokenBundle) -> NormalizedClaims:
        signing_key = _get_jwks().get_signing_key_from_jwt(tokens.access_token)
        claims = jwt.decode(
            tokens.access_token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=config.OIDC_ISSUER,
            options={"verify_aud": False},
        )
        roles = claims.get("realm_access", {}).get("roles", [])
        return NormalizedClaims(
            provider=self.name,
            sub=claims.get("sub", ""),
            email=claims.get("email"),
            name=claims.get("name") or claims.get("preferred_username"),
            roles=roles,
        )

    async def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        logout_url = (
            f"{config.KEYCLOAK_INTERNAL_URL}/realms/{config.KEYCLOAK_REALM}"
            "/protocol/openid-connect/logout"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                logout_url,
                data={
                    "client_id": config.KEYCLOAK_CLIENT_ID,
                    "client_secret": config.KEYCLOAK_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                },
            )
    async def refresh(self, refresh_token: str) -> TokenBundle:
        token_url = (
            f"{config.KEYCLOAK_INTERNAL_URL}/realms/{config.KEYCLOAK_REALM}"
            "/protocol/openid-connect/token"
        )
        data = {
            "grant_type": "refresh_token",
            "client_id": config.KEYCLOAK_CLIENT_ID,
            "client_secret": config.KEYCLOAK_CLIENT_SECRET,
            "refresh_token": refresh_token,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(token_url, data=data)

        if resp.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail=f"Keycloak token refresh failed: {resp.text}",
            )

        payload = resp.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise HTTPException(status_code=502, detail="No access token returned")

        return TokenBundle(
            access_token=access_token,
            refresh_token=payload.get("refresh_token") or refresh_token,
            id_token=payload.get("id_token"),
            expires_in=payload.get("expires_in", 300),
            refresh_expires_in=payload.get("refresh_expires_in"),
            raw=payload,
        )
