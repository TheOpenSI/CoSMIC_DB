### Core modules ###
from pydantic import ConfigDict


### Type hints ###
from pydantic.types import (
    UUID7,
    AwareDatetime
)
from ...types.json_schemas import ChatHistorySchemaUpdate


### Internal modules ###
from ..base_models import ChatboxBase



"""
To understand how this file structured, take a look at:
https://fastapi.tiangolo.com/tutorial/sql-databases/#update-the-app-with-multiple-models
"""
class ChatboxPublic(ChatboxBase):
    id:         UUID7
    create_on:  AwareDatetime


class ChatboxCreate(ChatboxBase):
    model_config = ConfigDict(extra="forbid")

    pass


class ChatboxUpdate(ChatboxBase):
    model_config = ConfigDict(extra="forbid")

    user_id:    UUID7 | None                            = None
    name:       str | None                              = None
    details:    list[ChatHistorySchemaUpdate] | None    = None


class ChatboxDelete(ChatboxBase):
    id:         UUID7
    create_on:  AwareDatetime
