from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class TokenBundle:
    access_token: str
    refresh_token: str | None = None
    id_token: str | None = None
    expires_in: int = 300
    refresh_expires_in: int | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class NormalizedClaims:
    provider: str
    sub: str
    email: str | None = None
    name: str | None = None
    roles: list[str] = field(default_factory=list)


class OAuthProvider(ABC):
    name: str

    @abstractmethod
    def authorize_url(self, state: str, redirect_uri: str) -> str:
        """Build IdP authorize URL."""

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> TokenBundle:
        """Swap authorization code for tokens."""

    @abstractmethod
    def normalize_claims(self, tokens: TokenBundle) -> NormalizedClaims:
        """Map IdP tokens → one Cosmic claim shape."""

    @abstractmethod
    async def logout(self, refresh_token: str | None) -> None:
        """Optional IdP-side logout."""

    @abstractmethod
    async def refresh(self, refresh_token: str) -> TokenBundle:
        """Refresh the access token."""