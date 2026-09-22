### Core modules ###
from fastapi import (
    APIRouter,
    HTTPException,
    status, 
    Query
)
from sqlmodel import select
from datetime import (
    datetime,
    timezone
)


### Type hints ###
from typing import Any
from pydantic.types import UUID7
from ...types.tags import APITag


### Internal modules ###
from ...cores.db import SessionDependency
from ...cores.globals import (OPENAPI_GET_EXTRA_RESPONSES,MONTH_LABELS,get_rolling_year_months)
from ...apis.table_models.users import Users
from ...apis.table_models.chatboxes import Chatboxes
from ...types.api_responses.tokens import (
    # For client responses (Responses Model)
    SystemTokenPublicResponse,
    UserTokenPublicResponse,
    ChatboxSessionTokenPublicResponse,
    InquiryCycleTokenPublicResponse,
    UserTokenRollingStatsResponse
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
    path="/user/{user_id}/rolling",
    status_code=status.HTTP_200_OK,
    response_model=UserTokenRollingStatsResponse,
    responses={**OPENAPI_GET_EXTRA_RESPONSES}
)
async def read_user_token_rolling_v1(
    user_id: UUID7,
    session: SessionDependency,
    months: int = Query(default=3, ge=3, le=12),
) -> Any:
    if months not in (3, 6, 12):
        raise HTTPException(status_code=400, detail="months must be 3, 6, or 12")
    # same 404 as GET /user/{user_id}
    if session.get(Users, user_id) is None:
        raise HTTPException(status_code=404, detail="User Not Found!")
    year_months = get_rolling_year_months(months)
    window_start = datetime(
        year_months[0][0], year_months[0][1], 1, tzinfo=timezone.utc
    )
    chatboxes_db = session.exec(
        select(Chatboxes.details).where(Chatboxes.user_id == user_id)
    ).all()
    input_by: dict[tuple[int, int], int] = {}
    output_by: dict[tuple[int, int], int] = {}
    for chatbox in chatboxes_db:
        if not chatbox:
            continue
        for chat_history in chatbox:
            ts = chat_history.get("query_create_on")
            if ts is None:
                continue
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts < window_start:
                continue
            key = (ts.year, ts.month)
            inp, out = get_io_token(payload=chat_history)
            input_by[key] = input_by.get(key, 0) + inp
            output_by[key] = output_by.get(key, 0) + out
    spans_multiple_years = len({y for y, _ in year_months}) > 1
    labels, input_totals, output_totals = [], [], []
    for year, month in year_months:
        if spans_multiple_years:
            labels.append(f"{MONTH_LABELS[month - 1]} '{str(year)[2:]}'")
        else:
            labels.append(MONTH_LABELS[month - 1])
        input_totals.append(input_by.get((year, month)))    
        output_totals.append(output_by.get((year, month)))
    return {
        "success": True,
        "user_id": user_id,
        "months": months,
        "labels": labels,
        "input_totals": input_totals,
        "output_totals": output_totals,
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
