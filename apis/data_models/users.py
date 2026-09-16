### Core modules ###
from pydantic import ConfigDict


### Type hints ###
from pydantic.types import (
    UUID7,
    AwareDatetime
)
from pydantic.networks import EmailStr


### Internal modules ###
from ..base_models import UserBase



"""
To understand how this file structured, take a look at:
https://fastapi.tiangolo.com/tutorial/sql-databases/#update-the-app-with-multiple-models
"""
class UserPublic(UserBase):
    email:      EmailStr | None = None
    id:         UUID7
    create_on:  AwareDatetime




class UserUpdate(UserBase):
    model_config = ConfigDict(extra="forbid")   # pyright: ignore

    role_id:    UUID7 | None    = None   # pyright: ignore
    name:       str | None      = None   # pyright: ignore
    email:      EmailStr | None = None


class UserDelete(UserBase):
    email:      EmailStr | None = None
    id:         UUID7
    create_on:  AwareDatetime
