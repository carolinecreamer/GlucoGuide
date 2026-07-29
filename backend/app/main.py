from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401
from app.api.routes import router
from app.core.database import create_schema


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_schema()
    yield


app = FastAPI(
    title="GlucoGuide API",
    version="0.1.0",
    description=(
        "Advisory-only diabetes pattern detection and meal/exercise guidance. "
        "No automated dosing or pump control."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

