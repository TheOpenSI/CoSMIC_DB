# config.py — Auth BFF settings (Keycloak-only, Authlib)
#
# NOTE:
# Google & Microsoft are no longer configured here. They are brokered by
# Keycloak (see `docker/keycloak/cosmic-realm.json`) so the BFF only ever talks
# to a single OpenID Connect provider.

### Core modules ###
from pathlib import Path


### Type hints ###


### Internal modules ###
from .env import get_env


cosmic_auth_configs: dict[str, str | None] = get_env()

# ── Shared BFF ──────────────────────────────────────────────────────────────
AUTH_PUBLIC_URL: str = (
    cosmic_auth_configs.get("AUTH_PUBLIC_URL")
    or "http://localhost:8081"
)
FRONTEND_URL: str = (
    cosmic_auth_configs.get("FRONTEND_URL")
    or "http://localhost:5173"
)
AUTH_API_PREFIX: str = "/api/v1/auth"

# ── Cosmic session (app-issued JWT, RS256) ──────────────────────────────────
SESSION_COOKIE_NAME: str = (
    cosmic_auth_configs.get("SESSION_COOKIE_NAME")
    or "cosmic_session"
)
SESSION_MAX_AGE: int = int(cosmic_auth_configs.get("SESSION_MAX_AGE") or "900")
REFRESH_COOKIE_MAX_AGE: int = int(cosmic_auth_configs.get("REFRESH_COOKIE_MAX_AGE") or "86400")
SESSION_ISSUER: str = cosmic_auth_configs.get("SESSION_ISSUER") or "cosmic-auth"

# Static RSA keypair used to sign/verify the Cosmic session cookie. The private
# key never leaves this service; the public half is published at
# `{AUTH_API_PREFIX}/jwks.json` for the other microservices.
SESSION_PRIVATE_KEY_PATH: Path = Path(
    cosmic_auth_configs.get("SESSION_PRIVATE_KEY_PATH")
    or (Path(__file__).resolve().parent / "secrets" / "session_private.pem")
)
SESSION_PUBLIC_KEY_PATH: Path = Path(
    cosmic_auth_configs.get("SESSION_PUBLIC_KEY_PATH")
    or (Path(__file__).resolve().parent / "secrets" / "session_public.pem")
)
# Optional explicit key id; falls back to the RFC 7638 thumbprint of the key.
SESSION_KEY_ID: str | None = cosmic_auth_configs.get("SESSION_KEY_ID")

# ── Starlette SessionMiddleware (holds temporary Authlib OAuth state/nonce) ──
SESSION_SECRET: str = (
    cosmic_auth_configs.get("SESSION_SECRET")
    or "cosmic-insecure-dev-secret"
)
OAUTH_SESSION_COOKIE: str = (
    cosmic_auth_configs.get("OAUTH_SESSION_COOKIE")
    or "cosmic_oauth_session"
)

# Legacy cookies. Names are kept so we can clear them for one release after the
# migration to Authlib + RS256.
ACCESS_TOKEN_COOKIE: str = "cosmic_access_token"
REFRESH_TOKEN_COOKIE: str = "cosmic_refresh_token"
OAUTH_STATE_COOKIE: str = "cosmic_oauth_state"
OAUTH_PROVIDER_COOKIE: str = "cosmic_oauth_provider"

# ── Keycloak ────────────────────────────────────────────────────────────────
KEYCLOAK_INTERNAL_URL: str = (
    cosmic_auth_configs.get("KEYCLOAK_INTERNAL_URL")
    or "http://cosmic-keycloak:8080"
)
KEYCLOAK_PUBLIC_URL: str = (
    cosmic_auth_configs.get("KEYCLOAK_PUBLIC_URL")
    or "http://localhost:8080"
)
KEYCLOAK_REALM: str = cosmic_auth_configs.get("KEYCLOAK_REALM") or "cosmic"
KEYCLOAK_CLIENT_ID: str | None = cosmic_auth_configs.get("KEYCLOAK_CLIENT_ID")
KEYCLOAK_CLIENT_SECRET: str | None = cosmic_auth_configs.get("KEYCLOAK_CLIENT_SECRET")
OIDC_ISSUER: str = f"{KEYCLOAK_PUBLIC_URL}/realms/{KEYCLOAK_REALM}"

_KEYCLOAK_REALM_PATH: str = f"/realms/{KEYCLOAK_REALM}/protocol/openid-connect"


def keycloak_authorize_url() -> str:
    """Browser-facing authorize endpoint (public host)."""
    return f"{KEYCLOAK_PUBLIC_URL}{_KEYCLOAK_REALM_PATH}/auth"


def keycloak_token_url() -> str:
    """Container-facing token endpoint (internal host)."""
    return f"{KEYCLOAK_INTERNAL_URL}{_KEYCLOAK_REALM_PATH}/token"


def keycloak_jwks_url() -> str:
    """Container-facing JWKS endpoint (internal host)."""
    return f"{KEYCLOAK_INTERNAL_URL}{_KEYCLOAK_REALM_PATH}/certs"


def keycloak_logout_url() -> str:
    """Browser-facing RP-initiated logout endpoint (public host)."""
    return f"{KEYCLOAK_PUBLIC_URL}{_KEYCLOAK_REALM_PATH}/logout"


def callback_url(provider: str = "keycloak") -> str:
    """Callback URL — must match the IdP console redirect URI."""
    return f"{AUTH_PUBLIC_URL}{AUTH_API_PREFIX}/callback/{provider}"
