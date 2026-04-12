"""Serve the Restate SDK endpoint on a dedicated port.

The Restate server discovers workflows by calling this endpoint.
Runs alongside the main FastAPI app on a separate port (default 9080).
"""

import uvicorn

from pipeline.app import restate_app


def main() -> None:
    uvicorn.run(
        restate_app,
        host="0.0.0.0",
        port=9080,
        log_level="info",
    )


if __name__ == "__main__":
    main()
