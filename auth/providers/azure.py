from dataclasses import dataclass, field
from typing import Protocol

from urllib.parse import urlencode

import httpx
import jwt
from fastapi import HTTPException
from jwt import PyJWKClient

from auth import config
from auth.providers.base import NormalizedClaims, TokenBundle



class AzureProvider:
    name = "azure"

    def authorize_url(self, state: str, redirect_uri: str) -> str:
        if not config.AZURE_AD_CLIENT_ID:
            raise HTTPException(status_code=500, detail="AZURE_AD_CLIENT_ID not configured")

        params = {
            "client_id": config.AZURE_AD_CLIENT_ID,
            "response_type": "code",
            "scope": "openid profile email offline_access",
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{config.AZURE_AD_AUTH_URL}?{urlencode(params)}"
        
        """Build IdP authorize URL."""

    async def exchange_code(self, code: str, redirect_uri: str) -> TokenBundle:
        if not config.AZURE_AD_CLIENT_ID or not config.AZURE_AD_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="Azure AD OAuth not configured")

        data = {
            "client_id": config.AZURE_AD_CLIENT_ID,
            "client_secret": config.AZURE_AD_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(config.AZURE_AD_TOKEN_URL, data=data)  
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail="Failed to exchange authorization code for tokens")

        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to exchange authorization code for tokens")

        payload = resp.json()
        access_token = payload.get("access_token")
        id_token = payload.get("id_token")
        if not access_token or not id_token:
            raise HTTPException(status_code=500, detail="Azure AD did not return access_token/id_token")

        return TokenBundle(
            access_token=access_token,
            id_token=id_token,
            refresh_token=payload.get("refresh_token"),
            expires_in=payload.get("expires_in", 3600),
            refresh_expires_in=None,  # azure omits this
            raw=payload,
        )
        """Swap authorization code for tokens."""

    def normalize_claims(self, tokens: TokenBundle) -> NormalizedClaims:
        if not tokens.id_token:
            raise HTTPException(status_code=500, detail="Missing id_token in Azure AD response")

        signing_key_url = config.AZURE_AD_JWKS_URL
        try:
            jwks_client = PyJWKClient(signing_key_url)
            signing_key = jwks_client.get_signing_key_from_jwt(tokens.id_token)
            decoded_token = jwt.decode(
                
                tokens.id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=config.AZURE_AD_CLIENT_ID,
                #issuer=config.AZURE_AD_ISSUER
            )
        except jwt.PyJWTError as e:
            raise HTTPException(status_code=500, detail="Failed to decode id_token")

        return NormalizedClaims(
            provider=self.name,
            sub=decoded_token.get("sub", ""),
            email=decoded_token.get("email"),
            name=decoded_token.get("name") or decoded_token.get("preferred_username"),
            roles=[], #no roles as of the momment
        )
    
        """Map IdP tokens → one Cosmic claim shape."""

    async def logout(self, refresh_token: str | None) -> None:
        pass  # Azure AD does not provide a standard logout endpoint for refresh tokens

        """Optional IdP-side logout."""