FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev

COPY . .

RUN useradd --create-home app
USER app

EXPOSE 8012

CMD [".venv/bin/python", "scripts/run_server.py"]
