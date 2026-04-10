import socketio

from assistant_ws.config import settings

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.cors_origins_list,
    max_http_buffer_size=1_048_576,
)

from assistant_ws.ws.events import register_events  # noqa: E402

register_events(sio)
