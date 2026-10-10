from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from auth import config, keys
from auth.routes import auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast (instead of at first login) when the RS256 session keypair is
    # missing or unreadable.
    keys.private_key()
    keys.public_key()
    yield


app = FastAPI(title="CoSMIC Auth API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authlib's web client keeps the temporary OAuth state/nonce in the session.
app.add_middleware(
    SessionMiddleware,
    secret_key=config.SESSION_SECRET,
    session_cookie=config.OAUTH_SESSION_COOKIE,
    same_site="lax",
    https_only=config.AUTH_PUBLIC_URL.startswith("https://"),
)

app.include_router(auth_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
