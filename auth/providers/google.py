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
        _jwks_client = PyJWKClient(config.GOOGLE_JWKS_URL)
    return _jwks_client


class GoogleProvider:
    name = "google"

    def authorize_url(self, state: str, redirect_uri: str) -> str:
        if not config.GOOGLE_CLIENT_ID:
            raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")

        params = {
            "client_id": config.GOOGLE_CLIENT_ID,
            "response_type": "code",
            "scope": "openid email profile",
            "redirect_uri": redirect_uri,
            "state": state,
            "access_type": "offline",  # helpful later for refresh; ok to keep
            "prompt": "consent",       # ensures refresh_token on first consent
        }
        return f"{config.GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenBundle:
        if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="Google OAuth not configured")

        data = {
            "grant_type": "authorization_code",
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        try :
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(config.GOOGLE_TOKEN_URL, data=data)
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Google token exchange failed: {e}")

        if resp.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"Google token exchange failed: {resp.text}",
            )

        payload = resp.json()
        access_token = payload.get("access_token")
        id_token = payload.get("id_token")
        if not access_token or not id_token:
            raise HTTPException(
                status_code=502,
                detail="Google did not return access_token/id_token",
            )

        return TokenBundle(
            access_token=access_token,
            refresh_token=payload.get("refresh_token"),
            id_token=id_token,
            expires_in=payload.get("expires_in", 3600),
            refresh_expires_in=None,  # Google often omits this
            raw=payload,
        )

    def normalize_claims(self, tokens: TokenBundle) -> NormalizedClaims:
        if not tokens.id_token:
            raise HTTPException(status_code=502, detail="Missing Google id_token")

        signing_key = _get_jwks().get_signing_key_from_jwt(tokens.id_token)
        claims = jwt.decode(
            tokens.id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=config.GOOGLE_CLIENT_ID,
            issuer=["https://accounts.google.com", "accounts.google.com"],
            leeway=60, # 60 seconds leeway for clock skew between Google and Cosmic wsl container 
        )
        return NormalizedClaims(
            provider=self.name,
            sub=claims.get("sub", ""),
            email=claims.get("email"),
            name=claims.get("name") or claims.get("email"),
            roles=[],  # Google has no Cosmic roles — Phase 3 uses Postgres
        )

    async def logout(self, refresh_token: str | None) -> None:
        # Optional: revoke at Google. Clearing Cosmic cookies is enough for now.
        if not refresh_token:
            return
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    data={"token": refresh_token},
                )
        except httpx.HTTPError:
            return

    async def refresh(self, refresh_token: str) -> TokenBundle:
        token_url = config.GOOGLE_TOKEN_URL
        data = {
            "grant_type": "refresh_token",
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "scope": "openid email profile",

        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(token_url, data=data)
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail=f"Google token refresh failed: {resp.text}")
        payload = resp.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise HTTPException(status_code=502, detail="No access token returned")
        return TokenBundle(
            access_token=access_token,
            refresh_token=payload.get("refresh_token") or refresh_token,
            id_token=payload.get("id_token"),
            expires_in=payload.get("expires_in", 3600),
            refresh_expires_in=None,  # Google often omits this
            raw=payload,
        )

