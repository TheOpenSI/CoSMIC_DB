### Core modules ###
from pathlib import Path


### Type hints ###


### Internal modules ###
from .env import get_env


cosmic_auth_configs: dict[str, str | None] = get_env()


### BFF Framework ###
AUTH_PUBLIC_URL: str | None = cosmic_auth_configs.get(
    "AUTH_PUBLIC_URL",
    "http://localhost:8081"
)
FRONTEND_URL: str | None = cosmic_auth_configs.get(
    "FRONTEND_URL",
    "http://localhost:5173"
)


### CoSMIC session ###
SESSION_COOKIE_NAME: str | None = cosmic_auth_configs.get(
    "SESSION_COOKIE_NAME",
    "cosmic_session"
)
SESSION_MAX_AGE: int = int(
    cosmic_auth_configs.get("SESSION_MAX_AGE")
    or
    "900"
)
SESSION_REFRESH_TOKEN_MAX_AGE: int = int(
    cosmic_auth_configs.get("SESSION_REFRESH_TOKEN_MAX_AGE")
    or
    "86400"
)
SESSION_ISSUER: str | None = cosmic_auth_configs.get(
    "SESSION_ISSUER",
    "cosmic-auth"
)
SESSION_PRIVATE_KEY_PATH: Path | None = Path(
    cosmic_auth_configs.get("SESSION_PRIVATE_KEY_PATH")
    or
    Path(__file__).resolve().parent.joinpath(
        "secrets",
        "session_private.pem"
    )
)
SESSION_PUBLIC_KEY_PATH: Path = Path(
    cosmic_auth_configs.get("SESSION_PUBLIC_KEY_PATH")
    or
    Path(__file__).resolve().parent.joinpath(
        "secrets",
        "session_public.pem"
    )
)
SESSION_KEY_ID: str | None = cosmic_auth_configs.get(
    "SESSION_KEY_ID",
    None
)

### Starlette SessionMiddleware (holds temporary Authlib OAuth state/nonce) ###
SESSION_SECRET: str | None = cosmic_auth_configs.get(
    "SESSION_SECRET",
    None
)
SESSION_OAUTH_COOKIE: str | None = cosmic_auth_configs.get(
    "OAUTH_SESSION_COOKIE",
    "cosmic_oauth_session"
)


### Keycloak (Google & Microsoft IdPs are integrated by default) ###
KEYCLOAK_INTERNAL_URL: str | None = cosmic_auth_configs.get(
    "KEYCLOAK_INTERNAL_URL",
    "http://cosmic-keycloak:8080"
)
KEYCLOAK_PUBLIC_URL: str | None = cosmic_auth_configs.get(
    "KEYCLOAK_PUBLIC_URL",
    "http://localhost:8080"
)
KEYCLOAK_REALM: str | None = cosmic_auth_configs.get(
    "KEYCLOAK_REALM",
    "cosmic"
)
KEYCLOAK_CLIENT_ID: str | None = cosmic_auth_configs.get(
    "KEYCLOAK_CLIENT_ID",
    None
)
KEYCLOAK_CLIENT_SECRET: str | None = cosmic_auth_configs.get(
    "KEYCLOAK_CLIENT_SECRET",
    None
)


### Other global configs ###
OIDC_ISSUER:            str = f"{KEYCLOAK_PUBLIC_URL}/realms/{KEYCLOAK_REALM}"
KEYCLOAK_REALM_PATH:    str = f"/realms/{KEYCLOAK_REALM}/protocol/openid-connect"


def keycloak_authorise_url() -> str:
    """Browser-facing authorise endpoint (public host)"""
    return f"{KEYCLOAK_PUBLIC_URL}{KEYCLOAK_REALM_PATH}/auth"


def keycloak_token_url() -> str:
    """Container-facing token endpoint (internal host)"""
    return f"{KEYCLOAK_INTERNAL_URL}{KEYCLOAK_REALM_PATH}/token"


def keycloak_jwks_url() -> str:
    """Container-facing JWKS endpoint (internal host)"""
    return f"{KEYCLOAK_INTERNAL_URL}{KEYCLOAK_REALM_PATH}/certs"


def keycloak_logout_url() -> str:
    """Browser-facing RP-initiated logout endpoint (public host)"""
    return f"{KEYCLOAK_PUBLIC_URL}{KEYCLOAK_REALM_PATH}/logout"


def callback_url(provider: str = "keycloak") -> str:
    """Callback URL (must match the IdP console redirect URI)"""
    return f"{AUTH_PUBLIC_URL}/api/v1/auth/callback/{provider}"
