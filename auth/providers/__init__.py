from fastapi import HTTPException

from auth import config
from auth.providers.base import OAuthProvider
from auth.providers.google import GoogleProvider
from auth.providers.keycloak import KeycloakProvider
from auth.providers.azure import AzureProvider

_PROVIDERS: dict[str, OAuthProvider] = {
    "keycloak": KeycloakProvider(),
    "google": GoogleProvider(),
    "azure": AzureProvider(),
}


def get_provider(name: str) -> OAuthProvider:
    key = name.strip().lower()
    if key not in config.ENABLED_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Provider '{key}' is not enabled")
    provider = _PROVIDERS.get(key)
    if provider is None:
        raise HTTPException(status_code=404, detail=f"Unknown provider '{key}'")
    return provider


def list_enabled_providers() -> list[str]:
    return [p for p in config.ENABLED_PROVIDERS if p in _PROVIDERS]