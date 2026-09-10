# config.py — Auth BFF settings (Keycloak + Google)

from .env import get_env

cosmic_auth_configs: dict[str, str | None] = get_env()

# ── Shared BFF ──────────────────────────────────────────────────────────────
AUTH_PUBLIC_URL = cosmic_auth_configs.get("AUTH_PUBLIC_URL", "http://localhost:8081")
FRONTEND_URL = cosmic_auth_configs.get("FRONTEND_URL", "http://localhost:5173")
AUTH_API_PREFIX = "/api/v1/auth"

ENABLED_PROVIDERS = [
    p.strip().lower()
    for p in (cosmic_auth_configs.get("ENABLED_PROVIDERS") or "keycloak,google").split(",")
    if p.strip()
]

SESSION_SECRET = cosmic_auth_configs.get("SESSION_SECRET")
SESSION_COOKIE_NAME = cosmic_auth_configs.get("SESSION_COOKIE_NAME", "cosmic_session")
SESSION_MAX_AGE = int(cosmic_auth_configs.get("SESSION_MAX_AGE") or "86400")

# Legacy IdP token cookies (Phase 0–1). Cosmic session comes in Phase 1.
ACCESS_TOKEN_COOKIE = "cosmic_access_token"
REFRESH_TOKEN_COOKIE = "cosmic_refresh_token"
OAUTH_STATE_COOKIE = "cosmic_oauth_state"
OAUTH_PROVIDER_COOKIE = "cosmic_oauth_provider"


def callback_url(provider: str) -> str:
    """Per-provider callback — must match IdP console redirect URI."""
    return f"{AUTH_PUBLIC_URL}{AUTH_API_PREFIX}/callback/{provider}"


# ── Keycloak ────────────────────────────────────────────────────────────────
KEYCLOAK_INTERNAL_URL = cosmic_auth_configs.get("KEYCLOAK_INTERNAL_URL", "http://cosmic-keycloak:8080")
KEYCLOAK_PUBLIC_URL = cosmic_auth_configs.get("KEYCLOAK_PUBLIC_URL", "http://localhost:8080")
KEYCLOAK_REALM = cosmic_auth_configs.get("KEYCLOAK_REALM", "cosmic")
KEYCLOAK_CLIENT_ID = cosmic_auth_configs.get("KEYCLOAK_CLIENT_ID")
KEYCLOAK_CLIENT_SECRET = cosmic_auth_configs.get("KEYCLOAK_CLIENT_SECRET")
OIDC_ISSUER = f"{KEYCLOAK_PUBLIC_URL}/realms/{KEYCLOAK_REALM}"

# ── Google ──────────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID = cosmic_auth_configs.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = cosmic_auth_configs.get("GOOGLE_CLIENT_SECRET")
GOOGLE_AUTH_URL = cosmic_auth_configs.get(
    "GOOGLE_AUTH_URL", "https://accounts.google.com/o/oauth2/v2/auth"
)
GOOGLE_TOKEN_URL = cosmic_auth_configs.get(
    "GOOGLE_TOKEN_URL", "https://oauth2.googleapis.com/token"
)
GOOGLE_JWKS_URL = cosmic_auth_configs.get(
    "GOOGLE_JWKS_URL", "https://www.googleapis.com/oauth2/v3/certs"
)
GOOGLE_ISSUER = cosmic_auth_configs.get("GOOGLE_ISSUER", "https://accounts.google.com")

# ── Azure AD ─────────────────────────────────────────────────────────────────
AZURE_AD_CLIENT_ID = cosmic_auth_configs.get("AZURE_AD_CLIENT_ID")
AZURE_AD_TENANT_ID = cosmic_auth_configs.get("AZURE_AD_TENANT_ID")
AZURE_AD_CLIENT_SECRET = cosmic_auth_configs.get("AZURE_AD_CLIENT_SECRET")
AZURE_AD_ISSUER = f"https://login.microsoftonline.com/{AZURE_AD_TENANT_ID}/v2.0"

AZURE_AD_AUTH_URL  = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
AZURE_AD_TOKEN_URL = f"https://login.microsoftonline.com/common/oauth2/v2.0/token"
AZURE_AD_JWKS_URL  = f"https://login.microsoftonline.com/common/discovery/v2.0/keys"
