### Core modules ###
from pydantic import (
    BaseModel,
    ConfigDict
)


### Type hints ###


### Internal modules ###
from ...apis.data_models.tokens import TokenPublic



"""
Client responses format according to FE requirements.
"""
class TokensPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success:    bool
    count:      int
    result:     list[TokenPublic]


class TokenPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success:    bool
    result:     TokenPublic
