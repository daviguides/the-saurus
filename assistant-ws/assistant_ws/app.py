from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from assistant_ws.agents.shared.mcp import close_mcp
from assistant_ws.api.routes import router as api_router
from assistant_ws.config import settings
from assistant_ws.ws import sio


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Shutdown: close MCP connection
    await close_mcp()


fastapi_app = FastAPI(
    title="The Saurus Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

fastapi_app.include_router(api_router, prefix="/api/v1")

app = socketio.ASGIApp(sio, fastapi_app, socketio_path="/socket.io")
