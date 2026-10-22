### Core modules ###
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
    OPENAPI_DELETE_EXTRA_RESPONSES,
    SYSTEM_ROLES
)
from ...apis.table_models.roles import Roles
from ...apis.table_models.users import Users
from ...apis.data_models.roles import (
    # For validation (Data Model)
    RoleCreate,
    RoleUpdate
)
from ...types.api_responses.roles import (
    # For client responses (Responses Model)
    RolesPublicResponse,
    RoleCreateResponse,
    RolePublicResponse,
    RoleUpdateResponse,
    RoleDeleteResponse
)
from ...utils.auth_client import (
    create_iam_role,
    update_iam_role,
    delete_iam_role
)


roles_v1_router: APIRouter = APIRouter(
    prefix="/api/v1/roles",
    tags=[APITag.role]
)


@roles_v1_router.get(
    path="/",
    status_code=status.HTTP_200_OK,
    response_model=RolesPublicResponse
)
async def read_roles_v1(
    session: SessionDependency
) -> Any:
    roles_view: Sequence[Roles] = session.exec(statement=select(Roles)).all()
    total_roles: int = len(roles_view)

    if (total_roles == 0):
        return {
            "success": True,
            "count": total_roles, # 0
            "result": roles_view
        }
    else:
        return {
            "success": True,
            "count": total_roles, # all fetchable role data
            "result": roles_view
        }


@roles_v1_router.post(
    path="/",
    status_code=status.HTTP_201_CREATED,
    response_model=RoleCreateResponse,
    responses={**OPENAPI_POST_EXTRA_RESPONSES}
)
async def create_role_v1(
    role: RoleCreate,
    session: SessionDependency
) -> Any:
    # Validation against 'name' field in payload
    role_stored_name: tuple[UUID7, str] | None = session.exec(
        statement=select(
            Roles.id,
            Roles.name
        )
        .where(
            Roles.name.ilike(role.name)
        )
    ).first()

    if role_stored_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "409 - Conflict",
                "message": f"[{role_stored_name[1]}] already exists."
                }
            )

    role_data: dict[str, Any] = role.model_dump(
        mode="json"
    )
    role_name: str = str(role_data["name"]).strip()

    if not role_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "400 - Bad Request",
                "message": "Field [name] cannot be empty."
            }
        )

    role_data["name"] = role_name

    # IAM first: the local row is only a fallback mirror.
    await create_iam_role(
        name=role_name,
        desc=role_data.get("desc")
    )

    # Only perform INSERT query if payload actually contains new data
    role_db: Roles = Roles.model_validate(
        obj=role_data,
        strict=True
    )

    try:
        session.add(instance=role_db)
        session.commit()
        session.refresh(instance=role_db)

        return {
            "success": True,
            "created": role_db
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


@roles_v1_router.get(
    path="/{role_id}",
    status_code=status.HTTP_200_OK,
    response_model=RolePublicResponse,
    responses={**OPENAPI_GET_EXTRA_RESPONSES}
)
async def read_role_v1(
    role_id: UUID7,
    session: SessionDependency
) -> Any:
    role_view: Roles | None = session.get(entity=Roles, ident=role_id)

    if role_view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role Not Found!"
        )
    else:
        return {
            "success": True,
            "result": role_view
        }


@roles_v1_router.patch(
    path="/{role_id}",
    status_code=status.HTTP_200_OK,
    response_model=RoleUpdateResponse,
    responses={**OPENAPI_PATCH_EXTRA_RESPONSES}
)
async def update_role_v1(
    role_id: UUID7,
    role: RoleUpdate,
    session: SessionDependency
) -> Any:
    role_db: Roles | None = session.get(
        entity=Roles,
        ident=role_id
    )

    if role_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role Not Found!"
        )

    # NOTE:
    # Default system roles cannot be modified/renamed at application level
    if role_db.name.lower() in SYSTEM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "400 - Bad Request",
                "message": f"Default system role [{role_db.name}] cannot be modified."
            }
        )

    role_data: dict[str, Any] = role.model_dump(
            mode='json',
            exclude_unset=True
    )

    # Empty payload validation
    if not role_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "400 - Bad Request",
                "message": "Incoming data cannot be empty."
            }
        )

    # Validate that incoming values are different from current stored values
    # (both full/partial payloads)
    for (key, value) in role_data.items():
        stored_value: Any = getattr(
            role_db,
            key
        )

        # NOTE:
        # 'name' field is a little special since we accept case-insensitive
        # value for this one
        if (
                key == "name"
            and isinstance(
                    value,
                    str
                )
            and isinstance(
                    stored_value,
                    str
                )
        ):
            if stored_value.lower() == value.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "400 - Bad Request",
                        "message": "Incoming data must be different from current stored data."
                    }
                )

        elif stored_value == value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "400 - Bad Request",
                    "message": "Incoming data must be different from current stored data."
                }
            )

    # Uniqueness check for 'name' field value against other roles
    if "name" in role_data and role_data["name"] is not None:
        role_stored_name: tuple[UUID7, str] | None = session.exec(
            statement=select(
                Roles.id,
                Roles.name
            )
            .where(
                Roles.name.ilike(role_data["name"]),
                Roles.id != role_id
            )
        ).first()

        if role_stored_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "status": "409 - Conflict",
                    "message": f"[{role_stored_name[1]}] already exists."
                }
            )

    if "name" in role_data:
        if (
            role_data["name"] is None
            or
            not str(role_data["name"]).strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "400 - Bad Request",
                    "message": "Field [name] cannot be empty."
                }
            )

        role_data["name"] = str(role_data["name"]).strip()

    # IAM first: the local row is only a fallback mirror. A partial failure
    # after a Keycloak rename is handled idempotently by the Auth service.
    await update_iam_role(
        current_name=role_db.name,
        payload=role_data
    )

    try:
        role_db.sqlmodel_update(obj=role_data)

        session.add(instance=role_db)
        session.commit()
        session.refresh(instance=role_db)

        return {
            "success": True,
            "updated": role_db
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


@roles_v1_router.delete(
    path="/{role_id}",
    status_code=status.HTTP_200_OK,
    response_model=RoleDeleteResponse,
    responses={**OPENAPI_DELETE_EXTRA_RESPONSES}
)
async def delete_role_v1(
    role_id: UUID7,
    session: SessionDependency
) -> Any:
    role_gone: Roles | None = session.get(entity=Roles, ident=role_id)

    if role_gone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role Not Found!"
        )

    if role_gone.name.strip().lower() in SYSTEM_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "400 - Bad Request",
                "message": f"Default system role [{role_gone.name}] cannot be deleted."
            }
        )

    # The FK is ON DELETE CASCADE, so deleting a referenced role would silently
    # delete its users as well. Refuse instead.
    assigned_user: UUID7 | None = session.exec(
        statement=select(Users.id).where(
            Users.role_id == role_gone.id
        )
    ).first()

    if assigned_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "409 - Conflict",
                "message": f"Role [{role_gone.name}] is still assigned to one or more users."
            }
        )

    # IAM first: the local row is only a fallback mirror.
    await delete_iam_role(name=role_gone.name)

    session.delete(instance=role_gone)
    session.commit()

    return {
        "success": True,
        "deleted": role_gone
    }
