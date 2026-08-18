### Core modules ###
from pydantic import (
    BaseModel,
    ConfigDict
)


### Type hints ###


### Internal modules ###
from ...apis.data_models.tokens import (
    SystemTokenPublic,
    UserTokenPublic,
    ChatboxSessionTokenPublic,
    InquiryCycleTokenPublic
)



"""
Client responses format according to FE requirements.
"""
class SystemTokenPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success:    bool
    result:     SystemTokenPublic


class UserTokenPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success:    bool
    result:     UserTokenPublic


class ChatboxSessionTokenPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success:    bool
    result:     ChatboxSessionTokenPublic


class InquiryCycleTokenPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success:    bool
    result:     InquiryCycleTokenPublic
