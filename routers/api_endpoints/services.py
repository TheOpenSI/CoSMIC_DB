### Core modules ###
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status
)
from sqlmodel import select


### Type hints ###
from collections.abc import Sequence
from pydantic.types import PositiveInt
from sqlalchemy.exc import IntegrityError
from sqlmodel.sql.expression import SelectOfScalar
from ...types.tags import APITag
from typing import (
    Annotated,
    Any
)


### Internal modules ###
from ...apis.table_models.services import Services
from ...apis.data_models.services import (
    # For validation (Data Model)
    ServiceCreate,
    ServiceUpdate
)
from ...cores.db import SessionDependency
from ...cores.globals import (
    OPENAPI_GET_EXTRA_RESPONSES,
    OPENAPI_POST_EXTRA_RESPONSES,
    OPENAPI_PATCH_EXTRA_RESPONSES,
    OPENAPI_DELETE_EXTRA_RESPONSES
)
from ...interfaces.apis.services import ServiceImmutableFieldValidator
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
    session: SessionDependency,
    immutable_field_validator: Annotated[
        ServiceImmutableFieldValidator,
        Depends(ServiceImmutableFieldValidator)
    ]
) -> Any:
    # Validation against 'name' field in payload
    service_name_uniqueness: str | None = session.exec(
        statement=select(
            Services.name
        )
        .where(
            Services.name.ilike(service.name)
        )
    ).first()

    if service_name_uniqueness:
        if service_name_uniqueness in ServiceImmutableFieldValidator.RESERVED_VALUES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "status": "409 - Conflict",
                    "message": f"Default core service [{service_name_uniqueness}] has been reserved."
                }
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "409 - Conflict",
                "message": f"A service with the name [{service_name_uniqueness}] already exists."
            }
        )

    # Reject names mimicking a reserved core service (injection attempts)
    immutable_field_validator.validate_reserved_value(service.name)

    # Only perform INSERT query if payload actually contains new data
    service_db: Services = Services.model_validate(
        obj=service,
        strict=True
    )

    # Prefer service name to get stored in lowercase per db convention
    service_db.name = service_db.name.lower()

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
    session: SessionDependency,
    immutable_field_validator: Annotated[
        ServiceImmutableFieldValidator,
        Depends(ServiceImmutableFieldValidator)
    ]
) -> Any:
    # Reject any modification up front since default core services are immutable
    service_db: Services = immutable_field_validator.validate_immutable_target(service_id=service_id)

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
    if "name" in service_data:
        service_name: str = service_data["name"]

        # Reject names mimicking a reserved core service (injection attempts)
        immutable_field_validator.validate_reserved_value(candidate=service_name)

        if service_name.lower() == service_db.name.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "400 - Bad Request",
                    "message": f"Incoming service name [{service_name}] matched current service name [{service_db.name}]."
                }
            )

        # Prefer service name to get stored in lowercase per db convention
        service_name = service_name.lower()

        service_name_uniqueness: str | None = session.exec(
            statement=select(
                Services.name
            )
            .where(
                Services.name.ilike(service_name),
                Services.id != service_id
            )
        ).first()

        if service_name_uniqueness:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "status": "409 - Conflict",
                    "message": f"A service with the name [{service_name_uniqueness}] already exists."
                }
            )

        service_data["name"] = service_name

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
