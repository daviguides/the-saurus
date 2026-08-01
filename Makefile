LOGS_DIR := $(CURDIR)/logs
SHELL := /bin/bash

.PHONY: dev-ws dev-mcp dev-pipeline dev-app dev-ui dev-qdrant \
	log-pipeline log-ws log-mcp log-app log-ui \
	up down lint test setup \
	test-pipeline test-ws test-mcp test-all \
	pipeline-test assistant-test \
	eval-setup eval-langfuse eval-langfuse-down \
	eval-generate-pipeline eval-generate-assistant eval-run-pipeline \
	eval-pipeline eval-assistant eval-safety eval-all \
	eval-score-pipeline eval-score-assistant eval-update-baseline \
	eval-judge-concordance eval-residual-error \
	dev-restate register-restate stop-restate

$(LOGS_DIR):
	mkdir -p $(LOGS_DIR)

# ─── Development (interactive, foreground) ─────────────────────────

dev-pipeline:
	cd pipeline && uv run python scripts/run_server.py

dev-ws:
	cd assistant-ws && uv run python scripts/run_server.py

dev-mcp:
	cd papers-mcp && uv run python scripts/run_server.py

dev-app:
	cd app && pnpm dev

dev-ui:
	cd assistant-ui && pnpm dev:federated

dev-qdrant:
	docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant

# ─── Logged mode (background, output to logs/) ────────────────────
#
# Usage:  make log-pipeline
# Claude: tail -f logs/pipeline.log  (or Read tool on logs/pipeline.log)

log-pipeline:
	@mkdir -p $(LOGS_DIR)
	@cd pipeline && nohup uv run python scripts/run_server.py > $(LOGS_DIR)/pipeline.log 2>&1 & echo $$! > $(LOGS_DIR)/pipeline.pid
	@echo "Pipeline running (PID $$(cat $(LOGS_DIR)/pipeline.pid)), logs at $(LOGS_DIR)/pipeline.log"

log-ws:
	@mkdir -p $(LOGS_DIR)
	@cd assistant-ws && nohup uv run python scripts/run_server.py > $(LOGS_DIR)/assistant-ws.log 2>&1 & echo $$! > $(LOGS_DIR)/assistant-ws.pid
	@echo "Assistant WS running (PID $$(cat $(LOGS_DIR)/assistant-ws.pid)), logs at $(LOGS_DIR)/assistant-ws.log"

log-mcp:
	@mkdir -p $(LOGS_DIR)
	@cd papers-mcp && nohup uv run python scripts/run_server.py > $(LOGS_DIR)/papers-mcp.log 2>&1 & echo $$! > $(LOGS_DIR)/papers-mcp.pid
	@echo "Papers MCP running (PID $$(cat $(LOGS_DIR)/papers-mcp.pid)), logs at $(LOGS_DIR)/papers-mcp.log"

log-app:
	@mkdir -p $(LOGS_DIR)
	@cd app && nohup pnpm dev > $(LOGS_DIR)/app.log 2>&1 & echo $$! > $(LOGS_DIR)/app.pid
	@echo "App running (PID $$(cat $(LOGS_DIR)/app.pid)), logs at $(LOGS_DIR)/app.log"

log-ui:
	@mkdir -p $(LOGS_DIR)
	@cd assistant-ui && nohup pnpm dev:federated > $(LOGS_DIR)/assistant-ui.log 2>&1 & echo $$! > $(LOGS_DIR)/assistant-ui.pid
	@echo "Assistant UI running (PID $$(cat $(LOGS_DIR)/assistant-ui.pid)), logs at $(LOGS_DIR)/assistant-ui.log"

# Start core services in logged mode (pipeline + app)
log-core: log-pipeline log-app
	@echo "Core services started. Logs in $(LOGS_DIR)/"

# Start all services in logged mode
log-all: log-pipeline log-ws log-mcp log-app log-ui
	@echo "All services started. Logs in $(LOGS_DIR)/"

# Stop all logged services
log-stop:
	@for pidfile in $(LOGS_DIR)/*.pid; do \
		if [ -f "$$pidfile" ]; then \
			pid=$$(cat "$$pidfile"); \
			if kill -0 "$$pid" 2>/dev/null; then \
				kill "$$pid" && echo "Stopped $$(basename $$pidfile .pid) (PID $$pid)"; \
			fi; \
			rm -f "$$pidfile"; \
		fi; \
	done

# Clean log files
log-clean:
	rm -f $(LOGS_DIR)/*.log $(LOGS_DIR)/*.pid

# ─── Docker Compose ────────────────────────────────────────────────

up:
	docker compose up --build -d

down:
	docker compose down

# ─── Testing ───────────────────────────────────────────────────────

test-pipeline:
	cd pipeline && uv run pytest tests/ -v

test-ws:
	cd assistant-ws && uv run pytest tests/ -v

test-mcp:
	cd papers-mcp && uv run pytest tests/ -v

test-all: test-pipeline test-ws test-mcp
	@echo "All test suites passed."

test: test-all

# ─── Test Clients ──────────────────────────────────────────────────

pipeline-test:
	cd pipeline-test-client && uv run pipeline-test $(ARGS)

assistant-test:
	cd assistant-test-client && uv run assistant-test $(ARGS)

# ─── Quality ───────────────────────────────────────────────────────

lint:
	cd pipeline && uv run ruff check .
	cd assistant-ws && uv run ruff check .
	cd papers-mcp && uv run ruff check .

format:
	cd pipeline && uv run ruff format .
	cd assistant-ws && uv run ruff format .
	cd papers-mcp && uv run ruff format .

# ─── Setup ─────────────────────────────────────────────────────────

setup:
	cd pipeline && uv sync
	cd assistant-ws && uv sync
	cd papers-mcp && uv sync
	cd pipeline-test-client && uv sync
	cd assistant-test-client && uv sync
	cd app && pnpm install
	cd assistant-ui && pnpm install

# ─── Evals ─────────────────────────────────────────────────────────

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

eval-judge-concordance:
	cd evals && uv run python -m pipeline.golden.judge_concordance

eval-residual-error:
	cd evals && uv run python -m pipeline.golden.residual_error

# ─── Restate ──────────────────────────────────────────────────────

dev-restate:
	docker run --name restate_dev --rm -d \
	  -p 8080:8080 -p 9070:9070 -p 9071:9071 \
	  --add-host=host.docker.internal:host-gateway \
	  docker.restate.dev/restatedev/restate:latest
	@echo "Restate running on :8080 (ingress), :9070 (admin)"

dev-restate-endpoint:
	cd pipeline && uv run python scripts/run_restate_endpoint.py

log-restate-endpoint: | $(LOGS_DIR)
	@cd pipeline && nohup uv run python scripts/run_restate_endpoint.py \
		> $(LOGS_DIR)/restate-endpoint.log 2>&1 & echo $$! > $(LOGS_DIR)/restate-endpoint.pid
	@echo "Restate endpoint running (PID $$(cat $(LOGS_DIR)/restate-endpoint.pid)), logs at $(LOGS_DIR)/restate-endpoint.log"

register-restate:
	@curl -s localhost:9070/deployments -H "Content-Type: application/json" \
		-d '{"uri": "http://host.docker.internal:9080", "use_http_11": true}' | python3 -m json.tool
	@echo "Registered pipeline workflow with Restate"

stop-restate:
	docker stop restate_dev 2>/dev/null || true
	@kill $$(cat $(LOGS_DIR)/restate-endpoint.pid 2>/dev/null) 2>/dev/null || true
