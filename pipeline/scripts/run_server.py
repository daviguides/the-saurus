import logging

import uvicorn

from pipeline.config import settings

# Configure logging so agent debug info is visible
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

# Silence noisy Agno/Gemini generic error logs — our parsing.py handles these
logging.getLogger("agno").setLevel(logging.CRITICAL)
logging.getLogger("google_genai").setLevel(logging.WARNING)
# Reduce httpx noise (every HuggingFace/Gemini/Qdrant request logged at INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


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
