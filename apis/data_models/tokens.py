### Core modules ###
from pydantic import BaseModel


### Type hints ###
from pydantic.types import (
    UUID7,
    PositiveInt
)


### Internal modules ###



"""
To understand how this file structured, take a look at:
https://fastapi.tiangolo.com/tutorial/sql-databases/#update-the-app-with-multiple-models
"""
class TokenPublic(BaseModel):
    user_id:            UUID7 | None
    chat_session_id:    UUID7 | None
    request_pair_id:    UUID7 | None
    input_token:        PositiveInt
    output_token:       PositiveInt
