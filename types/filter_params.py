### Core modules ###
from pydantic import BaseModel
from sqlmodel import Field


### Type hints ###
from pydantic.types import UUID7


### Internal modules ###



class ServiceFilterParams(BaseModel):
    # NOTE:
    # There wasn't any clear explanation on FastAPI docs when they use this in
    # one of the examples. Take a look at linked Pydantic docs here for more
    # detail:
    # https://pydantic.dev/docs/validation/latest/api/pydantic/config/#pydantic.config.ConfigDict.extra
    # https://fastapi.tiangolo.com/tutorial/query-param-models/#forbid-extra-query-parameters
    model_config = {"extra": "forbid"}

    active:         bool | None = Field(default=None)
    memory_enable:  bool | None = Field(default=None)


class EmissionFilterParams(BaseModel):
    # NOTE:
    # There wasn't any clear explanation on FastAPI docs when they use this in
    # one of the examples. Take a look at linked Pydantic docs here for more
    # detail:
    # https://pydantic.dev/docs/validation/latest/api/pydantic/config/#pydantic.config.ConfigDict.extra
    # https://fastapi.tiangolo.com/tutorial/query-param-models/#forbid-extra-query-parameters
    model_config = {"extra": "forbid"}

    user_id:        UUID7 | None = Field(default=None)
    emission_id:    UUID7 | None = Field(default=None)
