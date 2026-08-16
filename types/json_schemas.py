### Core modules ###
from uuid import uuid7
from pydantic import (
    BaseModel,
    ConfigDict
)


### Type hints ###
from pydantic.types import (
    UUID7,
    AwareDatetime,
    PositiveInt
)


### Internal modules ###
from ..cores.db import cosmic_db_configs
from ..cores.globals import (
    USER_ROLE,
    LLM_ROLE
)



#==============================================================================#
#       Pydantic validation for incoming requests that modify data in          #
#                   'Configurations' db table JSONB column(s)                  #
#==============================================================================#
class GeneralConfigs(BaseModel):
    """docstring for GeneralConfigs."""
    model_config = ConfigDict(extra="forbid")

    provider:               str         = "ollama"
    model:                  str         = "qwen2.5:7b"
    is_quantised:           bool        = False
    seed:                   int         = 0
    # NOTE:
    # These 2 fields need to be defined and stored from an external mounted
    # volume data that's related to CoSMIC container.
    default_knowledge_path: str         = "/app/data/default/"
    temp_knowledge_path:    str         = "/app/data/temp/"
    # NOTE:
    # This read the specified key's value provided in `cores/cosmic_config.env`
    # file. I don't think this's the right solution to go for but it's the good
    # enough solution for now.
    api_key:                str | None  = cosmic_db_configs.get("OPENAI_API_KEY", None)


class QueryAnalyserConfigs(GeneralConfigs):
    """docstring for QueryAnalyserConfigs."""
    model_config = ConfigDict(extra="forbid")

    # NOTE:
    # On FE, 'Query Analyser' setting will be pre-filled by a default enabled
    # button that apply the same configs from 'General' setting. Unless some
    # special modifications needed (only 'Admin' can do this), this's the
    # default behaviour.
    pass


class ConfigurationSchema(BaseModel):
    """docstring for ConfigurationSchema."""
    model_config = ConfigDict(extra="forbid")

    general:        GeneralConfigs
    query_analyser: QueryAnalyserConfigs



#==============================================================================#
#       Pydantic validation for incoming requests that modify data in          #
#                   'Chatboxes' db table JSONB column(s)                       #
#==============================================================================#
class ChatHistorySchema(BaseModel):
    """docstring for ChatHistorySchema."""
    model_config = ConfigDict(extra="forbid")

    request_pair_id:    UUID7 = uuid7()
    user_role:          str = USER_ROLE # NOTE: per agreed solution from our team
    user_query:         str
    query_create_on:    AwareDatetime
    llm_role:           str = LLM_ROLE  # NOTE: per agreed solution from our team
    llm_response:       str
    response_create_on: AwareDatetime
    input_token:        PositiveInt     # For final response received from `/cosmic (POST)` endpoint
    output_token:       PositiveInt     # For final response received from `/cosmic (POST)` endpoint
