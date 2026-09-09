### Core modules ###
from pydantic import BaseModel


### Type hints ###
from pydantic.types import NonNegativeInt


### Internal modules ###



"""
To understand how this file structured, take a look at:
https://fastapi.tiangolo.com/tutorial/sql-databases/#update-the-app-with-multiple-models
"""
class SystemTokenPublic(BaseModel):
    system_input_token:     NonNegativeInt
    system_output_token:    NonNegativeInt


class UserTokenPublic(BaseModel):
    user_input_token:   NonNegativeInt
    user_output_token:  NonNegativeInt


class ChatboxSessionTokenPublic(BaseModel):
    chatbox_session_input_token:    NonNegativeInt
    chatbox_session_output_token:   NonNegativeInt


class InquiryCycleTokenPublic(BaseModel):
    inquiry_cycle_input_token:  NonNegativeInt
    inquiry_cycle_output_token: NonNegativeInt
