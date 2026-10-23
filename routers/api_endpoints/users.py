### Core modules ###
from fastapi import (
    APIRouter,
    HTTPException,
    status
)
from re import (
    IGNORECASE,
    MULTILINE,
    VERBOSE,
    findall
)
from sqlmodel import select


### Type hints ###
from pydantic.types import UUID7
from typing import Any
from uuid import UUID
from collections.abc import Sequence
from sqlalchemy.exc import IntegrityError
from ...types.tags import APITag


### Internal modules ###
from ...cores.db import SessionDependency
from ...cores.globals import (
    OPENAPI_GET_EXTRA_RESPONSES,
    OPENAPI_PATCH_EXTRA_RESPONSES,
    OPENAPI_DELETE_EXTRA_RESPONSES
)
from ...apis.table_models.roles import Roles
from ...apis.table_models.users import Users
from ...apis.data_models.users import (
    # For validation (Data Model)
    UserUpdate
)
from ...types.api_responses.users import (
    # For client responses (Responses Model)
    UsersPublicResponse,
    UserPublicResponse,
    UserUpdateResponse,
    UserDeleteResponse
)
from ...utils.auth_client import (
    update_iam_user,
    delete_iam_user
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

    # Validation against 'role_id' field in payload. This's very important so
    # that not a single unknown/custom role bypass the logic and leave IAM
    # pointing at a role our db cannot store.
    if "role_id" in user_data:
        if user_data["role_id"] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "400 - Bad Request",
                    "message": "Field [role_id] cannot be null."
                }
            )

        role: Roles | None = session.get(
            entity=Roles,
            ident=UUID(str(user_data["role_id"]))
        )

        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "404 - Not Found",
                    "message": "Role Not Found!"
                }
            )

    # Validation against 'name' field in payload
    if "name" in user_data:
        if (
            user_data["name"] is None
            or
            not str(user_data["name"]).strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "400 - Bad Request",
                    "message": "Field [name] cannot be empty."
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
            if findall(
                pattern=r"example|test|demo",
                string=user_data["email"],
                flags=(
                    IGNORECASE   |
                    MULTILINE    |
                    VERBOSE
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

    # We update specified user data in IAM first before safe falling back to our
    # db. Any partial failures after an IAM rename is handled idempotently by the
    # our auth micro-service
    await update_iam_user(
        user_id=str(user_id),
        payload=user_data
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
    user_gone: Users | None = session.get(
        entity=Users,
        ident=user_id
    )

    if user_gone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User Not Found!"
        )
    else:
        # We delete specified user data in IAM first before safe falling back to
        # our db
        await delete_iam_user(user_id=str(user_id))

        session.delete(instance=user_gone)
        session.commit()

        return {
            "success": True,
            "deleted": user_gone
        }
