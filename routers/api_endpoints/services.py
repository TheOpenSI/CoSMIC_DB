### Core modules ###
from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    status
)
from sqlmodel import select


### Type hints ###
from sqlmodel.sql.expression import SelectOfScalar
from typing import (
    Annotated,
    Any
)
from collections.abc import Sequence
from ...types.tags import APITag
from pydantic.types import PositiveInt
from sqlalchemy.exc import IntegrityError


### Internal modules ###
from ...cores.db import SessionDependency
from ...cores.globals import (
    CORE_SERVICES,
    OPENAPI_GET_EXTRA_RESPONSES,
    OPENAPI_POST_EXTRA_RESPONSES,
    OPENAPI_PATCH_EXTRA_RESPONSES,
    OPENAPI_DELETE_EXTRA_RESPONSES
)
from ...apis.table_models.services import Services
from ...apis.data_models.services import (
    # For validation (Data Model)
    ServiceCreate,
    ServiceUpdate
)
from ...types.api_responses.services import (
    # For client responses (Responses Model)
    ServicesPublicResponse,
    ServiceCreateResponse,
    ServicePublicResponse,
    ServiceUpdateResponse,
    ServiceDeleteResponse
)
from ...types.filter_params import (
    ServiceFilterParams
)



services_v1_router: APIRouter = APIRouter(
    prefix="/api/v1/services",
    tags=[APITag.service]
)


@services_v1_router.get(
    path="/",
    status_code=status.HTTP_200_OK,
    response_model=ServicesPublicResponse
)
async def read_services_v1(
    session: SessionDependency,
    filter_query: Annotated[
        ServiceFilterParams,
        Query(
            title="Services Filter",
            description="filter by active/deactive memory enabled/disabled services.",
            strict=True
        )
    ]
) -> Any:
    # Dynamic build SELECT queries with WHERE clause for filtering
    service_stmt: SelectOfScalar[Services] = select(Services)

    if filter_query.active is not None:
        service_stmt = service_stmt.where(Services.status == filter_query.active)

    if filter_query.memory_enable is not None:
        service_stmt = service_stmt.where(Services.memory_capability == filter_query.memory_enable)

    # Final result will differ depends on which SELECT query being executed if
    # filter applied or not
    services_view: Sequence[Services] = session.exec(statement=service_stmt).all()

    return {
        "success": True,
        "count": len(services_view),
        "result": services_view
    }


@services_v1_router.post(
    path="/",
    status_code=status.HTTP_201_CREATED,
    response_model=ServiceCreateResponse,
    responses={**OPENAPI_POST_EXTRA_RESPONSES}
)
async def create_service_v1(
    service: ServiceCreate,
    session: SessionDependency
) -> Any:
    # Validation against 'name' field in payload
    service_stored_name: tuple[int, str] | None = session.exec(
        statement=select(
            Services.id,
            Services.name
        )
        .where(
            Services.name.ilike(service.name)
        )
    ).first()

    if service_stored_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "409 - Conflict",
                "message": f"[{service_stored_name[1]}] service with same name already exists."
                }
            )


    # Only perform INSERT query if payload actually contains new data
    service_db: Services = Services.model_validate(
        obj=service,
        strict=True
    )

    session.add(instance=service_db)
    session.commit()
    session.refresh(instance=service_db)

    return {
        "success": True,
        "created": service_db
    }


@services_v1_router.get(
    path="/{service_id}",
    status_code=status.HTTP_200_OK,
    response_model=ServicePublicResponse,
    responses={**OPENAPI_GET_EXTRA_RESPONSES}
)
async def read_service_v1(
    service_id: PositiveInt,
    session: SessionDependency
) -> Any:
    service_view: Services | None = session.get(entity=Services, ident=service_id)

    if service_view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service Not Found!"
        )

    else:
        return {
            "success": True,
            "result": service_view
        }


@services_v1_router.patch(
    path="/{service_id}",
    status_code=status.HTTP_200_OK,
    response_model=ServiceUpdateResponse,
    responses={**OPENAPI_PATCH_EXTRA_RESPONSES}
)
async def update_service_v1(
    service_id: PositiveInt,
    service: ServiceUpdate,
    session: SessionDependency
) -> Any:
    service_db: Services | None = session.get(
        entity=Services,
        ident=service_id
    )

    if service_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service Not Found!"
        )

    service_data: dict[str, Any] = service.model_dump(
        mode="json",
        exclude_unset=True
    )

    # Empty payload validation
    if not service_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "400 - Bad Request",
                "message": "Incoming data cannot be empty."
            }
        )

    # Default core services name cannot be modified/renamed at application level
    if service_db.name.lower() in CORE_SERVICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "400 - Bad Request",
                "message": f"Default core service [{service_db.name}] cannot be modified."
            }
        )

    # Validate that incoming values are different from current stored values
    # (both full/partial payloads)
    for (key, value) in service_data.items():
        stored_value: Any = getattr(
            service_db,
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

    # Uniqueness check for 'name' field value against other services
    if "name" in service_data and service_data["name"] is not None:
        service_stored_name: tuple[int, str] | None = session.exec(
            statement=select(
                Services.id,
                Services.name
            )
            .where(
                Services.name.ilike(service_data["name"]),
                Services.id != service_id
            )
        ).first()

        if service_stored_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "status": "409 - Conflict",
                    "message": f"[{service_stored_name[1]}] service with same name already exists."
                }
            )


    # Only perform UPDATE query if payload actually contains new data
    try:
        service_db.sqlmodel_update(obj=service_data)

        session.add(instance=service_db)
        session.commit()
        session.refresh(instance=service_db)

        return {
            "success": True,
            "updated": service_db
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


@services_v1_router.delete(
    path="/{service_id}",
    status_code=status.HTTP_200_OK,
    response_model=ServiceDeleteResponse,
    responses={
        **OPENAPI_DELETE_EXTRA_RESPONSES,
        403: {
            "description": "Delete Active Service Denied",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "status": "403 - Forbidden",
                            "message": "string"
                        }
                    }
                }
            }
        }
    }
)
async def delete_service_v1(
    service_id: PositiveInt,
    session: SessionDependency
) -> Any:
    service_gone: Services | None = session.get(
        entity=Services,
        ident=service_id
    )

    if service_gone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service Not Found!"
        )

    else:
        if service_gone.status != False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "403 - Forbidden",
                    "message": "Please disable the service first before peforming this action!!"
                }
            )

        else:
            session.delete(instance=service_gone)
            session.commit()

            return {
                "success": True,
                "deleted": service_gone
            }
