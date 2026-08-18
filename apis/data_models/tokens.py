### Core modules ###
from pydantic import BaseModel


### Type hints ###
from pydantic.types import PositiveInt


### Internal modules ###



"""
To understand how this file structured, take a look at:
https://fastapi.tiangolo.com/tutorial/sql-databases/#update-the-app-with-multiple-models
"""
class SystemTokenPublic(BaseModel):
    system_input_token:     PositiveInt
    system_output_token:    PositiveInt


class UserTokenPublic(BaseModel):
    user_input_token:   PositiveInt
    user_output_token:  PositiveInt


class ChatboxSessionTokenPublic(BaseModel):
    chatbox_session_input_token:    PositiveInt
    chatbox_session_output_token:   PositiveInt


class InquiryCycleTokenPublic(BaseModel):
    inquiry_cycle_input_token:  PositiveInt
    inquiry_cycle_output_token: PositiveInt
