from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.crypto import load_keys
from app.db import pool, run_migrations
from app.routers import auth, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_keys()  # fail fast if card keys are missing / KMS is unreachable
    run_migrations()  # apply pending yoyo migrations before serving requests
    pool.open(wait=True)
    yield
    pool.close()


app = FastAPI(title="Sample Users API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,  # lets the browser send/receive the auth cookie cross-origin
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
