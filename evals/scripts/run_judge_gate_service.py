"""uvicorn launcher for the judge-gate scoring service."""

import logging

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> None:
    uvicorn.run("scoring.judge_gate_service:app", host="0.0.0.0", port=8013)


if __name__ == "__main__":
    main()
