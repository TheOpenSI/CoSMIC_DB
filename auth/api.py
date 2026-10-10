### Core modules ###
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import (
    FastAPI,
    status
)
from starlette.middleware.sessions import SessionMiddleware


### Type hints ###


### Internal modules ###
from . import (
    config,
    keys
)
from .routes import auth_v1_router


# TODO: Need some more research on this usage rather than the deprecation
# event: 'startup' & 'shutdown'
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Equivalent to 'startup' event

    # Fail fast (instead of at first login) when the RS256 session keypair is
    # missing or unreadable.
    keys.private_key()
    keys.public_key()

    # NOTE:
    # We keep this for now as I do plan to add some logging/health checks here
    # somewhere in the future (possibly?).
    yield

    # Equivalent to 'shutdown' event


cosmic_auth_app: FastAPI = FastAPI(
    lifespan=lifespan,
    title="CoSMIC Auth API"
)


# NOTE: enable CORS on application level (only on dev)
cosmic_auth_app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_credentials=True,
    allow_origins=[config.FRONTEND_URL],
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600
)


# Authlib's web client keeps the temporary OAuth state/nonce in the session.
cosmic_auth_app.add_middleware(
    middleware_class=SessionMiddleware,
    secret_key=config.SESSION_SECRET,
    session_cookie=config.OAUTH_SESSION_COOKIE,
    same_site="lax",
    https_only=config.AUTH_PUBLIC_URL.startswith("https://")
)

# Normal endpoints


# API endpoints (V1)
cosmic_auth_app.include_router(router=auth_v1_router)


@cosmic_auth_app.get(
    path="/health",
    status_code=status.HTTP_200_OK
)
async def health() -> dict[str, str]:
    return {"status": "ok"}
