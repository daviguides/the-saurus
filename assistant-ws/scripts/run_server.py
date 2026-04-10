import uvicorn

from assistant_ws.config import settings


def main():
    uvicorn.run(
        "assistant_ws.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
    )


if __name__ == "__main__":
    main()
