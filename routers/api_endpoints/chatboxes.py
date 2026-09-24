### Core modules ###
from uuid import (
    UUID,
    SafeUUID
)
from fastapi import (
    APIRouter,
    HTTPException,
    status
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql.expression import update
from sqlalchemy.sql.functions import func
from sqlmodel import select


### Type hints ###
from typing import Any
from collections.abc import Sequence
from ...types.tags import APITag
from pydantic.types import UUID7
from sqlalchemy.exc import IntegrityError
from fastapi.exceptions import ResponseValidationError
from sqlalchemy.sql.expression import Update
from sqlalchemy.sql.elements import (
    BinaryExpression,
    ColumnElement
)


### Internal modules ###
from ...cores.db import SessionDependency
from ...cores.globals import (
    OPENAPI_GET_EXTRA_RESPONSES,
    OPENAPI_POST_EXTRA_RESPONSES,
    OPENAPI_PATCH_EXTRA_RESPONSES,
    OPENAPI_DELETE_EXTRA_RESPONSES
)
from ...apis.table_models.chatboxes import Chatboxes
from ...apis.data_models.chatboxes import (
    # For validation (Data Model)
    ChatboxCreate,
    ChatboxUpdate
)
from ...types.api_responses.chatboxes import (
    # For client responses (Responses Model)
    ChatboxesPublicResponse,
    ChatboxCreateResponse,
    ChatboxPublicResponse,
    ChatboxUpdateResponse,
    ChatboxDeleteResponse
)
from ...utils.roles import validate_role_name


chatboxes_v1_router: APIRouter = APIRouter(
    prefix="/api/v1/chatboxes",
    tags=[APITag.chatbox]
)


CHAT_HISTORY_FIELDS: tuple[str, ...] = (
    "inquiry_cycle_id",
    "user_role",
    "user_query",
    "query_create_on",
    "llm_role",
    "llm_response",
    "response_create_on",
    "input_token",
    "output_token"
)


@chatboxes_v1_router.get(
    path="/",
    status_code=status.HTTP_200_OK,
    response_model=ChatboxesPublicResponse
)
async def read_chatboxes_v1(
    session: SessionDependency
) -> Any:
    chatboxes_view: Sequence[Chatboxes] = session.exec(statement=select(Chatboxes)).all()
    total_chatboxes: int = len(chatboxes_view)

    if (total_chatboxes == 0):
        return {
            "success": True,
            "count": total_chatboxes, # 0
            "result": chatboxes_view
        }
    else:
        return {
            "success": True,
            "count": total_chatboxes, # all fetchable chatboxes data
            "result": chatboxes_view
        }


@chatboxes_v1_router.post(
    path="/",
    status_code=status.HTTP_201_CREATED,
    response_model=ChatboxCreateResponse,
    responses={
        **OPENAPI_POST_EXTRA_RESPONSES,
        500: {
            "description": "Custom Pydantic Type Unconverted",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "status": "500 - Internal Server Error",
                            "message": "string"
                        }
                    }
                }
            }
        }
    }
)
async def create_chatbox_v1(
    chatbox: ChatboxCreate,
    session: SessionDependency
) -> Any:
    try:
        # NOTE:
        # Anyone might wonder why didn't we do any sort of creation validation
        # logic here? Since this particular endpoint here is being used to create
        # new chat session with (or without) a chat history, it's actually valid
        # usecase to have duplicate chat session data in the db. Why would it be?
        # Because, well, users are **REDACTED** :)
        chatbox_db: Chatboxes = Chatboxes.model_validate(
            obj=chatbox,
            strict=True
        )

        # NOTE:
        # Pydantic Docs have a very clear example which explain why I use this
        # approach here. Our case is slightly different since we had a complex
        # custom list class type, hence we need to normalise first so it becomes
        # a normal Python list. Reference link below:
        # https://pydantic.dev/docs/validation/latest/concepts/serialization#python-mode
        chat_history_data: list[dict[str, Any]] = [
            chat_history.model_dump(mode='json')
            for chat_history in chatbox_db.details
        ]


        # Make sure `user_role` & `llm_role` fields value matched our constant
        # values
        if not validate_role_name(chat_history_data=chat_history_data):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "400 - Bad Request",
                    "message": "Invalid chat history data for creates."
                }
            )

        # Only perform INSERT query if payload actually contains new data
        else:
            # NOTE:
            # Very much similar reason as above
            chatbox_db.details = chat_history_data # pyright: ignore

            session.add(instance=chatbox_db)
            session.commit()
            session.refresh(instance=chatbox_db)

            return {
                "success": True,
                "created": chatbox_db
            }


    except IntegrityError as sqlalchemy_exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "409 - Conflict",
                "message": f"{sqlalchemy_exc}"
            }
        )


    except TypeError as python_exc:
        # NOTE:
        # This one isn't likely to be catch that easy anymore since the only case
        # that would cause this's by performing ORM queries with non-standard
        # Python types (e.g., our custom `ChatHistorySchema` type). If anyone
        # would still want to test this (probably through an actual unit test
        # file), feels free to comment out [Line 178] to see the effect.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "500 - Internal Server Error",
                "message": f"{python_exc}"
            }
        )


@chatboxes_v1_router.get(
    path="/{chatbox_session_id}",
    status_code=status.HTTP_200_OK,
    response_model=ChatboxPublicResponse,
    responses={**OPENAPI_GET_EXTRA_RESPONSES}
)
async def read_chatbox_v1(
    chatbox_session_id: UUID7,
    session: SessionDependency
) -> Any:
    chatbox_view: Chatboxes | None = session.get(entity=Chatboxes, ident=chatbox_session_id)

    if chatbox_view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbox Session Not Found!"
        )
    else:
        return {
            "success": True,
            "result": chatbox_view
        }


@chatboxes_v1_router.patch(
    path="/{chatbox_session_id}",
    status_code=status.HTTP_200_OK,
    response_model=ChatboxUpdateResponse,
    responses={**OPENAPI_PATCH_EXTRA_RESPONSES}
)
async def update_chatbox_v1(
    chatbox_session_id: UUID7,
    chatbox: ChatboxUpdate,
    session: SessionDependency
) -> Any:
    try:


        # NOTE:
        # These are some cases that can be considered a valid request for updating
        # chatbox data:
        # 1. Full updates
        # 2. Partial updates
        #   2.1. Chat history updates
        #   2.2. Surgical chat history block updates

        chatbox_db: Chatboxes | None = session.get(
            entity=Chatboxes,
            ident=chatbox_session_id
        )

        if chatbox_db is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chatbox Not Found!"
            )

        chatbox_data: dict[str, Any] = chatbox.model_dump(
            mode="json",
            exclude_unset=True
        )

        # Empty payload validation
        if not chatbox_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "400 - Bad Request",
                    "message": "Incoming data cannot be empty."
                }
            )

        # We must never allow transfering chat sessions between user ID
        if "user_id" in chatbox_data:
            # NOTE:
            # It's much more safe and accurate to compare UUID value in its
            # original form (UUID Object). The compiler will now understand
            # that we're matching them in chronological logic instead.
            chatbox_payload_user_id: UUID = UUID(
                hex=chatbox_data["user_id"],
                version=7,
                is_safe=SafeUUID.safe
            )

            if chatbox_payload_user_id != chatbox_db.user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "400 - Bad Request",
                        "message": "Chatbox ownership (user ID) cannot be modified."
                    }
                )

        # Handle 'name' field update (if provided)
        if "name" in chatbox_data:
            chatbox_db.name = chatbox_data["name"]

            session.add(instance=chatbox_db)
            session.commit()
            session.refresh(instance=chatbox_db)

        # Handle 'details' field updates with a 3-layer validation strategy
        if (
            "details" in chatbox_data
            and chatbox_data["details"] is None
            or not chatbox_data["details"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "400 - Bad Request",
                    "message": "Incoming chat history data cannot be empty."
                }
            )

        else:
            ### 'details' field update (Layer 1) ###
            chat_history_incoming_data: list[dict[str, Any]] = chatbox_data["details"]
            chat_history_current_data: list[dict[str, Any]] = chatbox_db.details

            if len(chat_history_incoming_data) == len(chat_history_current_data):
                if not validate_role_name(chat_history_data=chat_history_incoming_data):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "status": "400 - Bad Request",
                            "message": f"Immutable field found within provided fields."
                        }
                    )

                else:
                    if all(
                        chat_history_field in chat_history_block
                        for chat_history_block in chat_history_incoming_data
                        for chat_history_field in CHAT_HISTORY_FIELDS
                    ):
                        ### Chat history updates (Layer 2) ###

                        # NOTE:
                        # This might be hard to read because we're trying to be
                        # dynamic by leverage the type check from ORM for running
                        # SQL query. The equivalent SQL syntax is:
                        #   UPDATE
                        #       chatboxes
                        #   SET
                        #       details = details::JSONB || [new_chat_history]::JSONB
                        #   WHERE
                        #       chatboxes.id = config_id
                        #   RETURNING
                        #       chatboxes.name,
                        #       chatboxes.details,
                        #       chatboxes.id,
                        #       chatboxes.create_on
                        chatbox_stmt: Update = (
                            update(table=Chatboxes)
                            .where(Chatboxes.id == chatbox_session_id)
                            .values({
                                Chatboxes.details: (
                                    func.cast(Chatboxes.details, JSONB)
                                ).op("||")(
                                    # We only need the extra record, but Python list
                                    # always start from index 0
                                    func.cast(chat_history_incoming_data, JSONB)
                                )
                            })
                            .returning(Chatboxes)
                        )
                        session.exec(statement=chatbox_stmt)
                        session.commit()
                        session.refresh(instance=chatbox_db)

                    else:
                        chat_history_block_new_data:      dict[ColumnElement, Any] = {}
                        chat_history_block_new_target:    BinaryExpression[Any] = Chatboxes.details

                        for (chat_history_index, chat_history_block) in enumerate(chat_history_incoming_data):
                            chat_history_current_block: dict[str, Any] = chat_history_current_data[chat_history_index]

                            for chat_history_mutable_field in (
                                "user_query",
                                "llm_response"
                            ):
                                if (
                                    chat_history_mutable_field in chat_history_block
                                    and chat_history_block[chat_history_mutable_field] != chat_history_current_block[chat_history_mutable_field]
                                ):
                                    chat_history_block_new_data[chat_history_block_new_target[chat_history_index][chat_history_mutable_field]] = chat_history_block[chat_history_mutable_field]

                        if chat_history_block_new_data:
                            ### Surgical chat history updates (Layer 3) ###

                            # NOTE:
                            # This might be hard to read because we're trying to be
                            # dynamic by leverage the type check from ORM for running
                            # SQL query. The equivalent SQL syntax is:
                            #   UPDATE
                            #       chatboxes
                            #   SET
                            #       chatboxes['details'][chat_history_index][current key] = <new value>
                            #   WHERE
                            #       chatboxes.id = chatbox_session_id
                            #   RETURNING
                            #       chatboxes.user_id,
                            #       chatboxes.name,
                            #       chatboxes.details
                            chatbox_stmt: Update = (
                                update(table=Chatboxes)
                                .where(Chatboxes.id == chatbox_session_id)
                                .values(chat_history_block_new_data)
                                .returning(Chatboxes)
                            )
                            session.exec(statement=chatbox_stmt)
                            session.commit()
                            session.refresh(instance=chatbox_db)

            if len(chat_history_incoming_data) < len(chat_history_current_data):
                if not validate_role_name(chat_history_data=chat_history_incoming_data):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "status": "400 - Bad Request",
                            "message": f"Immutable field found within provided fields."
                        }
                    )

                else:
                    ### Chat history updates (Layer 2) ###

                    # NOTE:
                    # This might be hard to read because we're trying to be
                    # dynamic by leverage the type check from ORM for running
                    # SQL query. The equivalent SQL syntax is:
                    #   UPDATE
                    #       chatboxes
                    #   SET
                    #       details = details::JSONB || [new_chat_history]::JSONB
                    #   WHERE
                    #       chatboxes.id = config_id
                    #   RETURNING
                    #       chatboxes.name,
                    #       chatboxes.details,
                    #       chatboxes.id,
                    #       chatboxes.create_on
                    chatbox_stmt: Update = (
                        update(table=Chatboxes)
                        .where(Chatboxes.id == chatbox_session_id)
                        .values({
                            Chatboxes.details: (
                                func.cast(Chatboxes.details, JSONB)
                            ).op("||")(
                                func.cast(chat_history_incoming_data, JSONB)
                            )
                        })
                        .returning(Chatboxes)
                    )
                    session.exec(statement=chatbox_stmt)
                    session.commit()
                    session.refresh(instance=chatbox_db)

        return {
            "success": True,
            "updated": chatbox_db
        }

    except IntegrityError as psycopg_err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "409 - Conflict",
                "message": f"{psycopg_err}"
            }
        )

    except TypeError as python_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "500 - Type Error",
                "message": f"{python_err}"
            }
        )

    except ResponseValidationError as fastapi_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "500 - Response Validation Error",
                "message": f"{fastapi_err}"
            }
        )


@chatboxes_v1_router.delete(
    path="/{chatbox_session_id}",
    status_code=status.HTTP_200_OK,
    response_model=ChatboxDeleteResponse,
    responses={**OPENAPI_DELETE_EXTRA_RESPONSES}
)
async def delete_chatbox_v1(
    chatbox_session_id: UUID7,
    session: SessionDependency
) -> Any:
    chatbox_gone: Chatboxes | None = session.get(entity=Chatboxes, ident=chatbox_session_id)

    if chatbox_gone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chatbox Not Found!"
        )
    else:
        session.delete(instance=chatbox_gone)
        session.commit()

        return {
            "success": True,
            "deleted": chatbox_gone
        }
