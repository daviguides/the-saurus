.PHONY: dev dev-ws dev-mcp dev-ui up down lint test

# Development (run each service individually)
dev-ws:
	cd assistant-ws && uv run python scripts/run_server.py

dev-mcp:
	cd papers-mcp && uv run python scripts/run_server.py

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

test:
	cd assistant-ws && uv run pytest tests/ -v
	cd papers-mcp && uv run pytest tests/ -v

# Setup
setup:
	cd assistant-ws && uv sync
	cd papers-mcp && uv sync
	cd assistant-ui && pnpm install
