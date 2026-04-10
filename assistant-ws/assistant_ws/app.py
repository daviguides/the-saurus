from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from assistant_ws.config import settings
from assistant_ws.api.routes import router as api_router
from assistant_ws.ws import sio


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


fastapi_app = FastAPI(
    title="AnswerThis Assistant",
    version="0.1.0",
    lifespan=lifespan,
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.include_router(api_router, prefix="/api/v1")

app = socketio.ASGIApp(sio, fastapi_app, socketio_path="/socket.io")
