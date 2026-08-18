### Core modules ###
from fastapi import (
    APIRouter,
    status
)


### Type hints ###
from typing import Any
from pydantic.types import UUID7
from ...types.tags import APITag


### Internal modules ###
from ...cores.db import SessionDependency
from ...cores.globals import OPENAPI_GET_EXTRA_RESPONSES
from ...types.api_responses.tokens import (
    # For client responses (Responses Model)
    SystemTokenPublicResponse,
    UserTokenPublicResponse,
    ChatboxSessionTokenPublicResponse,
    InquiryCycleTokenPublicResponse
)



tokens_v1_router: APIRouter = APIRouter(
    prefix="/api/v1/tokens",
    tags=[APITag.token]
)


@tokens_v1_router.get(
    path="/system",
    status_code=status.HTTP_200_OK,
    response_model=SystemTokenPublicResponse,
    responses={**OPENAPI_GET_EXTRA_RESPONSES}
)
async def read_system_token_v1(
    session: SessionDependency
) -> Any:
    return {
        "success": True,
        "result": {
            "system_input_token": 400,
            "system_output_token": 40
        }
    }


@tokens_v1_router.get(
    path="/user/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserTokenPublicResponse,
    responses={**OPENAPI_GET_EXTRA_RESPONSES}
)
async def read_user_token_v1(
    user_id: UUID7,
    session: SessionDependency
) -> Any:
    return {
        "success": True,
        "result": {
            "user_input_token": 300,
            "user_output_token": 30
        }
    }


@tokens_v1_router.get(
    path="/chatbox/{chatbox_session_id}",
    status_code=status.HTTP_200_OK,
    response_model=ChatboxSessionTokenPublicResponse,
    responses={**OPENAPI_GET_EXTRA_RESPONSES}
)
async def read_chatbox_session_token_v1(
    chatbox_session_id: UUID7,
    session: SessionDependency
) -> Any:
    return {
        "success": True,
        "result": {
            "chatbox_session_input_token": 200,
            "chatbox_session_output_token": 20
        }
    }


@tokens_v1_router.get(
    path="/inquiry/{inquiry_cycle_id}",
    status_code=status.HTTP_200_OK,
    response_model=InquiryCycleTokenPublicResponse,
    responses={**OPENAPI_GET_EXTRA_RESPONSES}
)
async def read_inquiry_cycle_token_v1(
    inquiry_cycle_id: UUID7,
    session: SessionDependency
) -> Any:
    return {
        "success": True,
        "result": {
            "inquiry_cycle_input_token": 100,
            "inquiry_cycle_output_token": 10
        }
    }
