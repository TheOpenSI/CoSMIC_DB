### Core modules ###
from fastapi import (
    APIRouter,
    HTTPException,
    status
)
from sqlmodel import select
from sqlalchemy.sql.dml import Update
from sqlalchemy.sql.expression import update


### Type hints ###
from typing import Any
from collections.abc import Sequence
from ...types.tags import APITag
from pydantic.types import UUID7
from sqlalchemy.exc import IntegrityError
from fastapi.exceptions import ResponseValidationError
from sqlalchemy.sql.elements import ColumnElement


### Internal modules ###
from ...cores.db import SessionDependency
from ...cores.globals import (
    OPENAPI_GET_EXTRA_RESPONSES,
    OPENAPI_POST_EXTRA_RESPONSES,
    OPENAPI_PATCH_EXTRA_RESPONSES,
    OPENAPI_DELETE_EXTRA_RESPONSES
)
from ...apis.table_models.configurations import Configurations
from ...apis.data_models.configurations import (
    # For validation (Data Model)
    ConfigurationCreate,
    ConfigurationUpdate
)
from ...types.api_responses.configurations import (
    # For client responses (Responses Model)
    ConfigurationsPublicResponse,
    ConfigurationCreateResponse,
    ConfigurationPublicResponse,
    ConfigurationUpdateResponse,
    ConfigurationDeleteResponse
)


configs_v1_router: APIRouter = APIRouter(
    prefix="/api/v1/configs",
    tags=[APITag.config]
)


@configs_v1_router.get(
    path="/",
    status_code=status.HTTP_200_OK,
    response_model=ConfigurationsPublicResponse
)
async def read_configs_v1(
    session: SessionDependency
) -> Any:
    configs_view: Sequence[Configurations] = session.exec(statement=select(Configurations)).all()
    total_configs: int = len(configs_view)

    if (total_configs == 0):
        return {
            "success": True,
            "count": total_configs, # 0
            "result": configs_view
        }
    else:
        return {
            "success": True,
            "count": total_configs, # all fetchable configs data
            "result": configs_view
        }


@configs_v1_router.post(
    path="/",
    status_code=status.HTTP_201_CREATED,
    response_model=ConfigurationCreateResponse,
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
async def create_config_v1(
    config: ConfigurationCreate,
    session: SessionDependency
) -> Any:
    try:
        # Validation against 'name' field in payload
        config_stored_name: tuple[UUID7, str | None] | None = session.exec(
            statement=select(
                Configurations.id,
                Configurations.name
            )
            .where(
                Configurations.name == config.name
            )
        ).first()

        if config_stored_name:
            if config_stored_name[1] is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "status": "409 - Conflict",
                        "message": f"[{config_stored_name[1]}] config preset has been created."
                        }
                    )

            else:
                # Different response message for NULL data rather than showing
                # literal 'None' value
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "status": "409 - Conflict",
                        "message": "This would cause confusion but an unknown config preset has been created. Recommended to update and give it a proper name."
                        }
                    )


        # Validation against 'details' field in payload
        config_stored_details: tuple[UUID7, dict[str, dict[str, Any]]] | None = session.exec(
            statement=select(
                Configurations.id,
                Configurations.details # pyright: ignore
            )
            .where(
                # NOTE:
                # Pydantic Docs have a very clear example which explain why I use
                # this approach here:
                # https://pydantic.dev/docs/validation/latest/concepts/serialization#python-mode
                Configurations.details == config.details.model_dump(mode='json')
            )
        ).first()

        if config_stored_details:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "status": "409 - Conflict",
                    "message": f"Exact [{config_stored_details[1]}] setting from one of the config preset has been found."
                    }
                )


        # Only perform INSERT query if payload actually contains new data
        config_db: Configurations = Configurations.model_validate(
            obj=config,
            strict=True
        )

        # NOTE:
        # Very much similar reason as above
        config_db.details = config_db.details.model_dump(mode='json') # pyright: ignore

        session.add(instance=config_db)
        session.commit()
        session.refresh(instance=config_db)

        return {
            "success": True,
            "created": config_db
        }


    except TypeError as python_exc:
        # NOTE:
        # This one isn't likely to be catch that easy anymore since the only case
        # that would cause this's by performing ORM queries with non-standard
        # Python types (e.g., our custom `ConfigurationSchema` type). If anyone
        # would still want to test this (probably through an actual unit test
        # file), feels free to comment out [Line 196] to see the effect.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "500 - Internal Server Error",
                "message": f"{python_exc}"
            }
        )


@configs_v1_router.get(
    path="/{config_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConfigurationPublicResponse,
    responses={**OPENAPI_GET_EXTRA_RESPONSES}
)
async def read_config_v1(
    config_id: UUID7,
    session: SessionDependency
) -> Any:
    config_view: Configurations | None = session.get(entity=Configurations, ident=config_id)

    if config_view is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration Not Found!"
        )
    else:
        return {
            "success": True,
            "result": config_view
        }


@configs_v1_router.patch(
    path="/{config_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConfigurationUpdateResponse,
    responses={**OPENAPI_PATCH_EXTRA_RESPONSES}
)
async def update_config_v1(
    config_id: UUID7,
    config: ConfigurationUpdate,
    session: SessionDependency
) -> Any:
    try:


        # NOTE:
        # These are some cases that can be considered a valid request for updating configuration data:
        # 1. Full updates
        # 2. Partial updates
        #     2.1. Simple key-value pairs
        #     2.2. Complex JSONB key-value pairs
        #         2.2.1. Full inner block updates
        #         2.2.2. Surgical inner block updates


        config_db: Configurations | None = session.get(
            entity=Configurations,
            ident=config_id
        )

        if config_db is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Configuration Not Found!"
            )

        config_data: dict[str, Any] = config.model_dump(
            mode="json",
            exclude_unset=True
        )

        # Empty payload validation
        if not config_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "400 - Bad Request",
                    "message": "Incoming data cannot be empty."
                }
            )

        # Handle 'name' field update (if provided)
        if "name" in config_data:
            config_incoming_name: str | None = config_data["name"]

            if config_incoming_name == config_db.name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "status": "400 - Bad Request",
                        "message": "Incoming data must be different from current stored data."
                    }
                )
            else:
                config_db.name = config_incoming_name

                session.add(instance=config_db)
                session.commit()
                session.refresh(instance=config_db)

        # Handle 'details' field updates with a 3-layer validation strategy
        if (
            "details" in config_data
            and config_data["details"] is not None
        ):
            config_incoming_preset_data: dict[str, dict[str, Any]] = config_data["details"]
            config_current_preset_data:  dict[str, dict[str, Any]] = config_db.details

            # Determine if this's a full config preset update (Layer 1)
            config_full_preset_update: bool = all(
                config_setting_field in config_incoming_preset_data
                for config_setting_field in (
                    "general",
                    "query_analyser"
                )
            )

            if config_full_preset_update:
                # Full payload update for 'details' (Layer 1)
                if config_incoming_preset_data == config_current_preset_data:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "status": "400 - Bad Request",
                            "message": "Stored configuration details exactly match the incoming full payload."
                        }
                    )

                # Check global uniqueness across other records
                config_current_preset_similarity: UUID7 | None = session.exec(
                    statement=select(
                        Configurations.id
                    ).where(
                        Configurations.details == config_incoming_preset_data,
                        Configurations.id != config_id
                    )
                ).first()

                if config_current_preset_similarity:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "status": "400 - Bad Request",
                            "message": "Another configuration preset with these exact details already exists."
                        }
                    )
                else:
                    config_db.details = config_incoming_preset_data

                    session.add(instance=config_db)
                    session.commit()
                    session.refresh(instance=config_db)

            else:
                # Partial payload updates for config settings (Layer 2 & 3)
                config_setting_new_data: dict[ColumnElement, Any] = {}
                CONFIG_SETTING_INNER_FIELDS: tuple[str, ...] = (
                    "provider",
                    "model",
                    "is_quantised",
                    "seed",
                    "default_knowledge_path",
                    "temp_knowledge_path",
                    "api_key"
                )

                for config_setting_field in (
                    "general",
                    "query_analyser"
                ):
                    if config_setting_field in config_incoming_preset_data:
                        config_setting_incoming_data:   dict[str, Any] = config_incoming_preset_data[config_setting_field]
                        config_setting_current_data:    dict[str, Any] = config_current_preset_data.get(
                            config_setting_field,
                            {}
                        )

                        # Filter out None values to strictly respect stored data
                        # for unpassed keys
                        config_setting_filtered_incoming_data: dict[str, Any] = {
                            config_setting_key: config_setting_value
                            for (config_setting_key, config_setting_value) in config_setting_incoming_data.items()
                            if config_setting_value is not None
                        }

                        if not config_setting_filtered_incoming_data:
                            continue

                        # Check if incoming filtered config setting data is an exact match to stored one
                        if config_setting_filtered_incoming_data == config_setting_current_data:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail={
                                    "status": "400 - Bad Request",
                                    "message": f"Stored [{config_setting_field}] settings exactly match the incoming data."
                                }
                            )

                        # Check if it's a 2nd layer full inner block update (all
                        # schema keys present and not None)
                        if set(CONFIG_SETTING_INNER_FIELDS).issubset(config_setting_filtered_incoming_data.keys()):
                            # Full inner fields replacement/concatenation (Layer 2)
                            config_current_preset_data[config_setting_field] = config_setting_filtered_incoming_data
                            config_setting_new_data[Configurations.details[config_setting_field]] = config_setting_filtered_incoming_data

                        else:
                            # Fully partial payload (surgical key-by-key subscripting) (Layer 3)
                            config_filtered_matching_keys: bool = True

                            for (config_filtered_setting_key, config_filtered_setting_value) in config_setting_filtered_incoming_data.items():
                                if (
                                    config_filtered_setting_key in config_setting_current_data
                                    and config_setting_current_data[config_filtered_setting_key] == config_filtered_setting_value
                                ):
                                    pass

                                else:
                                    config_filtered_matching_keys = False

                                # Map dynamic SQL JSONB subscript update for modified fields only
                                config_setting_new_data[Configurations.details[config_setting_field][config_filtered_setting_key]] = config_filtered_setting_value

                            if config_filtered_matching_keys:
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail={
                                        "status": "400 - Bad Request",
                                        "message": f"All provided fields in [{config_setting_field}] exactly match the stored data."
                                    }
                                 )

                # Only perform UPDATE query if payload actually contains new data
                if config_setting_new_data:
                    # NOTE:
                    # This might be hard to read because we're trying to be
                    # dynamic by leverage the type check from ORM for running SQL
                    # query. The equivalent SQL syntax is:
                    #   UPDATE
                    #       configurations
                    #   SET
                    #       configurations['details'][config_type][current key] = 
                    #   WHERE
                    #       configurations.id = config_id
                    #   RETURNING
                    #       configurations.user_id,
                    #       configurations.name,
                    #       configurations.details
                    config_stmt: Update = (
                        update(table=Configurations)
                        .where(Configurations.id == config_id)
                        .values(config_setting_new_data)
                        .returning(Configurations)
                    )
                    session.exec(statement=config_stmt)
                    session.commit()
                    session.refresh(instance=config_db)

        return {
            "success": True,
            "updated": config_db
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


@configs_v1_router.delete(
    path="/{config_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConfigurationDeleteResponse,
    responses={**OPENAPI_DELETE_EXTRA_RESPONSES}
)
async def delete_config_v1(
    config_id: UUID7,
    session: SessionDependency
) -> Any:
    config_gone: Configurations | None = session.get(entity=Configurations, ident=config_id)

    if config_gone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration Not Found!"
        )
    else:
        session.delete(instance=config_gone)
        session.commit()

        return {
            "success": True,
            "deleted": config_gone
        }
