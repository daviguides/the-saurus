import uvicorn

from pipeline.config import settings


def main():
    uvicorn.run(
        "pipeline.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=settings.workers,
    )


if __name__ == "__main__":
    main()
