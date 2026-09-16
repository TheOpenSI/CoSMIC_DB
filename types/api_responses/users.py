### Core modules ###
from pydantic import (
    BaseModel,
    ConfigDict
)


### Type hints ###


### Internal modules ###
from ...apis.data_models.users import (
    UserPublic,
    UserDelete
)



"""
Client responses format according to FE requirements.
"""
class UsersPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success:    bool
    count:      int
    result:     list[UserPublic]




class UserPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success:    bool
    result:     UserPublic


class UserUpdateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success:    bool
    updated:    UserPublic


class UserDeleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success:    bool
    deleted:    UserDelete
