.PHONY: dev dev-ws dev-mcp dev-pipeline dev-app dev-ui up down lint test \
	eval-setup eval-langfuse eval-langfuse-down eval-generate-pipeline \
	eval-generate-assistant eval-run-pipeline eval-pipeline eval-assistant \
	eval-safety eval-all eval-score-pipeline eval-score-assistant eval-update-baseline

# Development (run each service individually)
dev-ws:
	cd assistant-ws && uv run python scripts/run_server.py

dev-mcp:
	cd papers-mcp && uv run python scripts/run_server.py

dev-pipeline:
	cd pipeline && uv run python scripts/run_server.py

dev-app:
	cd app && pnpm dev

dev-ui:
	cd assistant-ui && pnpm dev

dev-qdrant:
	docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant

# Docker Compose
up:
	docker compose up --build -d

down:
	docker compose down

# Quality
lint:
	cd assistant-ws && uv run ruff check .
	cd papers-mcp && uv run ruff check .
	cd pipeline && uv run ruff check .

test:
	cd assistant-ws && uv run pytest tests/ -v
	cd papers-mcp && uv run pytest tests/ -v
	cd pipeline && uv run pytest tests/ -v

# Setup
setup:
	cd assistant-ws && uv sync
	cd papers-mcp && uv sync
	cd pipeline && uv sync
	cd app && pnpm install
	cd assistant-ui && pnpm install

# Evals
eval-setup:
	cd evals && uv sync

eval-langfuse:
	cd evals && docker compose up -d

eval-langfuse-down:
	cd evals && docker compose down

eval-generate-pipeline:
	cd evals && uv run python -m pipeline.golden.generate

eval-generate-assistant:
	cd evals && uv run python -m assistant.golden.generate

eval-run-pipeline:
	cd evals && uv run python -m pipeline.golden.run_pipeline

eval-pipeline:
	cd evals && uv run deepeval test run pipeline/tests/ -v

eval-assistant:
	cd evals && uv run deepeval test run assistant/tests/ -v

eval-safety:
	cd evals && uv run deepeval test run pipeline/tests/test_safety.py assistant/tests/test_safety.py -v

eval-all:
	cd evals && uv run deepeval test run pipeline/tests/ assistant/tests/ -v

eval-score-pipeline:
	cd evals && uv run python -m scoring.pipeline_scorer

eval-score-assistant:
	cd evals && uv run python -m scoring.assistant_scorer

eval-update-baseline:
	cd evals && uv run python -m pipeline.golden.update_baseline
