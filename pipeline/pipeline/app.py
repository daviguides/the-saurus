"""FastAPI application for the pipeline service."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from pipeline.api import router
from pipeline.config import settings
from pipeline.ws import websocket_stream


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.jobs_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="The Saurus Pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.websocket("/jobs/{job_id}/stream")
async def ws_stream(websocket: WebSocket, job_id: str) -> None:
    await websocket_stream(websocket, job_id, Path(settings.jobs_dir))
