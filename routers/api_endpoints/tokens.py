### Core modules ###
from fastapi import (
    APIRouter,
    HTTPException,
    status
)
from sqlmodel import select


### Type hints ###
from typing import Any
from pydantic.types import UUID7
from ...types.tags import APITag


### Internal modules ###
from ...cores.db import SessionDependency
from ...cores.globals import OPENAPI_GET_EXTRA_RESPONSES
from ...apis.table_models.users import Users
from ...apis.table_models.chatboxes import Chatboxes
from ...types.api_responses.tokens import (
    # For client responses (Responses Model)
    SystemTokenPublicResponse,
    UserTokenPublicResponse,
    ChatboxSessionTokenPublicResponse,
    InquiryCycleTokenPublicResponse
)
from ...utils.tokens import get_io_token



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
    chatboxes_db: list[list[dict[str, str | int]]] = session.exec(
        statement=select(
            Chatboxes.details
        )
    ).all()

    total_system_input_token:   int = 0
    total_system_output_token:  int = 0

    for chatbox in chatboxes_db:
        for chat_history in chatbox:
            (
                system_input_token,
                system_output_token
            ) = get_io_token(payload=chat_history)

            total_system_input_token    += system_input_token
            total_system_output_token   += system_output_token

    return {
        "success": True,
        "result": {
            "system_input_token": total_system_input_token,
            "system_output_token": total_system_output_token
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
    user_db: Users | None = session.get(
        entity=Users,
        ident=user_id
    )

    if user_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User Not Found!"
        )

    chatboxes_db: list[list[dict[str, str | int]]] = session.exec(
        statement=select(
            Chatboxes.details
        ).where(
            Chatboxes.user_id == user_id
        )
    ).all()

    total_user_input_token:     int = 0
    total_user_output_token:    int = 0

    for chatbox in chatboxes_db:
        for chat_history in chatbox:
            (
                user_input_token,
                user_output_token
            ) = get_io_token(payload=chat_history)

            total_user_input_token  += user_input_token
            total_user_output_token += user_output_token

    return {
        "success": True,
        "result": {
            "user_input_token": total_user_input_token,
            "user_output_token": total_user_output_token
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
    session:            SessionDependency
) -> Any:
    chatbox_db: Chatboxes | None = session.get(
        entity=Chatboxes,
        ident=chatbox_session_id
    )

    if chatbox_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbox Session Not Found!"
        )

    total_chatbox_session_input_token:  int = 0
    total_chatbox_session_output_token: int = 0

    if chatbox_db.details:
        for chat_history in chatbox_db.details:
            (
                chatbox_session_input_token,
                chatbox_session_output_token
            ) = get_io_token(payload=chat_history)

            total_chatbox_session_input_token   += chatbox_session_input_token
            total_chatbox_session_output_token  += chatbox_session_output_token

    return {
        "success": True,
        "result": {
            "chatbox_session_input_token": total_chatbox_session_input_token,
            "chatbox_session_output_token": total_chatbox_session_output_token
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
    chatboxes_db: list[list[dict[str, str | int]]] = session.exec(
        statement=select(
            Chatboxes.details
        )
    ).all()

    for chatbox in chatboxes_db:
        for chat_history in chatbox:
            if str(inquiry_cycle_id) == str(chat_history["inquiry_cycle_id"]):
                (
                    inquiry_cycle_input_token,
                    inquiry_cycle_output_token
                ) = get_io_token(payload=chat_history)

                return {
                    "success": True,
                    "result": {
                        "inquiry_cycle_input_token": inquiry_cycle_input_token,
                        "inquiry_cycle_output_token": inquiry_cycle_output_token
                    }
                }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Inquiry Cycle Not Found!"
    )
