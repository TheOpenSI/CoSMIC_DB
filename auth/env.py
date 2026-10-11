### Core modules ###
from pathlib import Path
from dotenv import dotenv_values


### Type hints ###


### Internal modules ###


def get_env() -> dict[str, str | None]:
    env_file: Path = (
        Path(__file__).resolve(strict=True).parent / "cosmic_auth.env"
    )

    return dotenv_values(
        dotenv_path=env_file,
        encoding="utf-8"
    )
