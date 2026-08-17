### Core modules ###
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


### Type hints ###


### Internal modules ###
from ..routers.api_endpoints.users import users_v1_router
from ..routers.api_endpoints.roles import roles_v1_router
from ..routers.api_endpoints.services import services_v1_router
from ..routers.api_endpoints.configurations import configs_v1_router
from ..routers.api_endpoints.chatboxes import chatboxes_v1_router
from ..routers.api_endpoints.emissions import emissions_v1_router
from ..routers.api_endpoints.tokens import tokens_v1_router


# TODO: Need some more research on this usage rather than the deprecation
# event: 'startup' & 'shutdown'
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Equivalent to 'startup' event

    # NOTE:
    # We keep this for now as I do plan to add some logging/health checks here
    # somewhere in the future (possibly?).
    yield

    # Equivalent to 'shutdown' event


cosmic_app: FastAPI = FastAPI(
    lifespan=lifespan,
    title="CoSMIC Database API"
)


# NOTE: enable CORS on application level (only on dev)
cosmic_app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_credentials=True,
    allow_origins=[
        "http://localhost:5173",    # FE binded Docker port
        "http://localhost:8000",    # BE binded Docker port
        "http://localhost:3000"     # CoSMIC binded Docker port
    ],
    allow_methods=[
        "POST",
        "PATCH",
        "GET",
        "DELETE"
    ],
    allow_headers=[],
    max_age=600
)


# Normal endpoints


# API endpoints (V1)
cosmic_app.include_router(router=users_v1_router)
cosmic_app.include_router(router=roles_v1_router)
cosmic_app.include_router(router=services_v1_router)
cosmic_app.include_router(router=configs_v1_router)
cosmic_app.include_router(router=chatboxes_v1_router)
cosmic_app.include_router(router=emissions_v1_router)
cosmic_app.include_router(router=tokens_v1_router)
