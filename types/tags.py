### Core modules ###
from enum import Enum


### Type hints ###


### Internal modules ###



"""
https://fastapi.tiangolo.com/tutorial/path-operation-configuration/?h=enum#tags-with-enums
"""
class APITag(Enum):
    """docstring for APITag."""
    user        = "Users API Endpoint"
    role        = "Roles API Endpoint"
    service     = "Services API Endpoint"
    config      = "Configurations API Endpoint"
    chatbox     = "Chatboxes API Endpoint"
    emission    = "Emissions API Endpoint"
    token       = "Tokens API Endpoint"
