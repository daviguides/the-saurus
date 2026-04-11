import logging

import uvicorn

from pipeline.config import settings

# Configure logging so agent debug info is visible
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

# Show Agno errors (ERROR level) to debug Gemini failures, but hide INFO/DEBUG noise
logging.getLogger("agno").setLevel(logging.ERROR)
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
        # Only watch Python source files — exclude jobs/ data (YAML, NDJSON, PDFs, markdown)
        reload_includes=["*.py"] if settings.reload else None,
        reload_excludes=["jobs/*", "*.yaml", "*.ndjson", "*.md", "*.pdf"] if settings.reload else None,
    )


if __name__ == "__main__":
    main()
