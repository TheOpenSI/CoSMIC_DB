### Core modules ###
from fastapi import Depends
from sqlmodel import (
    Session,
    create_engine
)


### Type hints ###
from collections.abc import Generator
from sqlalchemy.engine import Engine
from typing_extensions import (
    Annotated,
    Any
)


### Internal modules ###
from .configs import cosmic_db_configs


cosmic_db_dia:  str | None = cosmic_db_configs["DB_DIALECT"]
cosmic_db_dri:  str | None = cosmic_db_configs["DB_DRIVER"]
cosmic_db_usr:  str | None = cosmic_db_configs["DB_USER"]
cosmic_db_pwd:  str | None = cosmic_db_configs["DB_PASSWORD"]
cosmic_db_hst:  str | None = cosmic_db_configs["DB_HOST"]
cosmic_db_port: str | None = cosmic_db_configs["DB_PORT"]
cosmic_db_name: str | None = cosmic_db_configs["DB_NAME"]

cosmic_db_url: str = (
    "{0:s}+{1:s}://{2:s}:{3:s}@{4:s}:{5:s}/{6:s}".format(
        cosmic_db_dia,
        cosmic_db_dri,
        cosmic_db_usr,
        cosmic_db_pwd,
        cosmic_db_hst,
        cosmic_db_port,
        cosmic_db_name
    )
)

# NOTE: 'echo' param is for debug only!
cosmic_db_engine: Engine = create_engine(
    url=cosmic_db_url,
    echo=True
)


def get_session() -> Generator[Session, Any, Any]:
    # Using `with` keyword, it handles starting/closing session automatically
    with Session(bind=cosmic_db_engine) as session:
        yield session


SessionDependency = Annotated[Session, Depends(dependency=get_session)]
