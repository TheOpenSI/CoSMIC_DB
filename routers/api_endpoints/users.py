### Core modules ###
import re
from fastapi import (
    APIRouter,
    HTTPException,
    status
)
from sqlmodel import select


### Type hints ###
from pydantic.types import UUID7
from typing import Any
from collections.abc import Sequence
from ...types.tags import APITag
from sqlalchemy.exc import IntegrityError


### Internal modules ###
from ...cores.db import SessionDependency
from ...cores.globals import (
    OPENAPI_GET_EXTRA_RESPONSES,
    OPENAPI_POST_EXTRA_RESPONSES,
    OPENAPI_PATCH_EXTRA_RESPONSES,
    OPENAPI_DELETE_EXTRA_RESPONSES
)
from ...apis.table_models.users import Users
from ...apis.data_models.users import (
    # For validation (Data Model)
    UserCreate,
    UserUpdate
)
from ...types.api_responses.users import (
    # For client responses (Responses Model)
    UsersPublicResponse,
    UserCreateResponse,
    UserPublicResponse,
    UserUpdateResponse,
    UserDeleteResponse
)


users_v1_router: APIRouter = APIRouter(
    prefix="/api/v1/users",
    tags=[APITag.user]
)


@users_v1_router.get(
    path="/",
    status_code=status.HTTP_200_OK,
    response_model=UsersPublicResponse
)
async def read_users_v1(
    session: SessionDependency
) -> Any:
    users_view: Sequence[Users] = session.exec(statement=select(Users)).all()
    total_users: int = len(users_view)

    if (total_users == 0):
        return {
            "success": True,
            "count": total_users, # 0
            "result": users_view
        }
    else:
        return {
            "success": True,
            "count": total_users, # all fetchable user data
            "result": users_view
        }


@users_v1_router.post(
    path="/",
    status_code=status.HTTP_201_CREATED,
    response_model=UserCreateResponse,
    responses={**OPENAPI_POST_EXTRA_RESPONSES}
)
async def create_user_v1(
    user: UserCreate,
    session: SessionDependency
) -> Any:
    try:
        # Validation against 'name' field in payload
        user_stored_name: tuple[UUID7, str] | None = session.exec(
            statement=select(
                Users.id,
                Users.name
            )
            .where(
                Users.name == user.name
            )
        ).first()

        if user_stored_name:
            # NOTE:
            # We tried to utilise what 're' offered by default so it looks quite
            # special than a normal RegEx. The original form (assume using `/` as
            # default delims) is:
            #                           "/example|test|demo/gmix"
            if re.findall(
                pattern=r"example|test|demo",
                string=user_stored_name[1],
                flags=(
                    re.IGNORECASE   |
                    re.MULTILINE    |
                    re.VERBOSE
                )
            ):
                # Different response message for these special users since it can
                # only be created by us admins for testing purposes
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "status": "409 - Conflict",
                        "message": "A test/demo user has been created. Feels free to use it directly."
                        }
                    )


        # Validation against 'email' field in payload
        user_stored_email: tuple[UUID7, str | None] | None = session.exec(
            statement=select(
                Users.id,
                Users.email
            )
            .where(
                Users.email == user.email
            )
        ).first()

        if user_stored_email:
            if user_stored_email[1] is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "status": "409 - Conflict",
                        "message": f"An user with [{user_stored_email[1]}] email has been registered."
                        }
                    )

            else:
                # Different response message for NULL data rather than showing
                # literal 'None' value
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "status": "409 - Conflict",
                        "message": "A test/demo account has been created. Feels free to use it directly."
                        }
                    )


        # Only perform INSERT query if payload actually contains new data
        user_db: Users = Users.model_validate(
            obj=user,
            strict=True
        )

        session.add(instance=user_db)
        session.commit()
        session.refresh(instance=user_db)

        return {
            "success": True,
            "created": user_db
        }


    except IntegrityError as sqlalchemy_exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "409 - Conflict",
                "message": f"{sqlalchemy_exc}"
            }
        )


@users_v1_router.get(
    path="/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserPublicResponse,
    responses={**OPENAPI_GET_EXTRA_RESPONSES}
)
async def read_user_v1(
    user_id: UUID7,
    session: SessionDependency
) -> Any:
    user_view: Users | None = session.get(entity=Users, ident=user_id)

    if user_view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User Not Found!"
        )
    else:
        return {
            "success": True,
            "result": user_view
        }


@users_v1_router.patch(
    path="/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserUpdateResponse,
    responses={**OPENAPI_PATCH_EXTRA_RESPONSES}
)
async def update_user_v1(
    user_id: UUID7,
    user: UserUpdate,
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

    user_data: dict[str, Any] = user.model_dump(
        mode='json',
        exclude_unset=True
    )

    # Empty payload validation
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "400 - Bad Request",
                "message": "Incoming data cannot be empty."
            }
        )

    # Validate that incoming values are different from current stored values
    # (both full/partial payloads)
    for (key, value) in user_data.items():
        if getattr(user_db, key) == value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "400 - Bad Request",
                    "message": "Incoming data must be different from current stored data."
                }
            )

    # Validation against 'email' field in payload
    if "email" in user_data:
        if user_data["email"] is not None:
            # NOTE:
            # We tried to utilise what 're' offered by default so it looks quite
            # special than a normal RegEx. The original form (assume using `/` as
            # default delims) is:
            #                       "/example|test|demo/gmix"
            if re.findall(
                pattern=r"example|test|demo",
                string=user_data["email"],
                flags=(
                    re.IGNORECASE   |
                    re.MULTILINE    |
                    re.VERBOSE
                )
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "400 - Bad Request",
                        "message": "An email with test/demo domains or usernames is reserved for test/demo accounts only."
                    }
                )

        else:
            # Different response message for NULL data rather than showing
            # literal 'None' value
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "status": "400 - Bad Request",
                    "message": "This action is only allowed for test/demo accounts."
                    }
                )

        # Uniqueness check for email against other users
        user_stored_email: tuple[UUID7, str | None] | None = session.exec(
            statement=select(
                Users.id,
                Users.email
            )
            .where(
                Users.email == user_data["email"],
                Users.id != user_id
            )
        ).first()

        if user_stored_email and user_stored_email[1] is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "status": "409 - Conflict",
                    "message": f"An user with [{user_stored_email[1]}] email has been registered."
                }
            )


    # Only perform UPDATE query if payload actually contains new data
    try:
        user_db.sqlmodel_update(obj=user_data)

        session.add(instance=user_db)
        session.commit()
        session.refresh(instance=user_db)

        return {
            "success": True,
            "updated": user_db
        }

    except IntegrityError as sqlalchemy_exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "409 - Conflict",
                "message": f"{sqlalchemy_exc}"
            }
        )


@users_v1_router.delete(
    path="/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserDeleteResponse,
    responses={**OPENAPI_DELETE_EXTRA_RESPONSES}
)
async def delete_user_v1(
    user_id: UUID7,
    session: SessionDependency
) -> Any:
    user_gone: Users | None = session.get(entity=Users, ident=user_id)

    if user_gone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User Not Found!"
        )
    else:
        session.delete(instance=user_gone)
        session.commit()

        return {
            "success": True,
            "deleted": user_gone
        }
