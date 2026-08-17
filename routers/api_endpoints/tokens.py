### Core modules ###
from uuid import UUID
from fastapi import (
    APIRouter,
    Query,
    status
)


### Type hints ###
from typing import (
    Annotated,
    Any
)
from ...types.tags import APITag
from ...types.filter_params import TokenFilterParams


### Internal modules ###
from ...cores.globals import OPENAPI_GET_EXTRA_RESPONSES
from ...types.api_responses.tokens import (
    # For client responses (Responses Model)
    TokensPublicResponse,
    TokenPublicResponse
)


tokens_v1_router: APIRouter = APIRouter(
    prefix="/api/v1/tokens",
    tags=[APITag.token]
)


@tokens_v1_router.get(
    path="/",
    status_code=status.HTTP_200_OK,
    response_model=TokensPublicResponse | TokenPublicResponse,
    responses={**OPENAPI_GET_EXTRA_RESPONSES}
)
async def read_tokens_v1(
    filter_query: Annotated[
        TokenFilterParams,
        Query(
            title="Tokens Filter",
            description="filter by user ID, chat session ID, or request pair ID.",
            strict=True
        )
    ]
) -> Any:
    # Get only the filter data that were actually provided by the client
    token_filter_data: dict[str, UUID] = filter_query.model_dump(exclude_unset=True)

    # If ANY filter data is present, handle the filtered response
    if token_filter_data:
        return {
            "success": True,
            "result": {
                "user_id": filter_query.user_id,
                "chat_session_id": filter_query.chat_session_id,
                "request_pair_id": filter_query.request_pair_id,
                "input_token": 1,
                "output_token": 1,
            }
        }
    else:
        # Otherwise, perform the general GET (no filters applied)
        return {
            "success": True,
            "count": 0,
            "result": []
        }
