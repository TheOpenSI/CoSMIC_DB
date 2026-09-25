### Core modules ###
from pydantic import ConfigDict


### Type hints ###
from pydantic.types import (
    PositiveInt,
    AwareDatetime
)


### Internal modules ###
from ..base_models import ServiceBase



"""
To understand how this file structured, take a look at:
https://fastapi.tiangolo.com/tutorial/sql-databases/#update-the-app-with-multiple-models
"""
class ServicePublic(ServiceBase):
    id:         PositiveInt
    create_on:  AwareDatetime


class ServiceCreate(ServiceBase):
    model_config = ConfigDict(extra="forbid")   # pyright: ignore

    pass


class ServiceUpdate(ServiceBase):
    model_config = ConfigDict(extra="forbid")   # pyright: ignore

    name:               str | None  = None      # pyright: ignore
    desc:               str | None  = None
    status:             bool | None = None      # pyright: ignore
    memory_capability:  bool | None = None      # pyright: ignore


class ServiceDelete(ServiceBase):
    id:         PositiveInt
    create_on:  AwareDatetime
