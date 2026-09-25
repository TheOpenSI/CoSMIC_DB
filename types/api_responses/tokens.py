### Core modules ###
from pydantic import (
    BaseModel,
    ConfigDict
)



### Type hints ###
from pydantic.types import UUID7


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


class UserTokenRollingStatsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success:        bool
    user_id:        UUID7
    months:         int
    labels:         list[str]
    input_totals:   list[int | None]
    output_totals:  list[int | None] 
