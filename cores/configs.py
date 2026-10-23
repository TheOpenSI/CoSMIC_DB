### Core modules ###
from dotenv import dotenv_values
from pathlib import Path


### Type hints ###


### Internal modules ###


def get_db_env() -> dict[str, str | None]:
    env_file: Path = Path(__file__).resolve(strict=True).parent.joinpath(
        "cosmic_cfg.env"
    )

    return dotenv_values(
        dotenv_path=env_file,
        encoding= "utf-8"
    )


cosmic_db_configs: dict[str, str | None] = get_db_env()


### Auth BFF IAM management API ###
# Used by users or roles API endpoints to push IAM mutations before writing it
# back to our own db for safe fallback
COSMIC_AUTH_URL: str | None = cosmic_db_configs.get(
    "COSMIC_AUTH_URL",
    "http://cosmic-keycloak-fastapi:8081"
)
