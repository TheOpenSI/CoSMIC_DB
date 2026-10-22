### Core modules ###


### Type hints ###


### Internal modules ###
from .env import get_env


cosmic_db_configs: dict[str, str | None] = get_env()


### Auth BFF IAM management API ###
# Used by the user/role endpoints to push IAM mutations before writing the
# fallback local row.
COSMIC_AUTH_URL: str = str(
    cosmic_db_configs.get("COSMIC_AUTH_URL")
    or
    "http://cosmic-keycloak-fastapi:8081"
)
