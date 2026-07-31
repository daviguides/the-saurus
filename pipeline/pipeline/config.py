"""Pipeline configuration (pydantic-settings, PIPELINE_ prefix)."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Pipeline settings loaded from environment variables."""

    model_config = {"env_prefix": "PIPELINE_", "env_file": ".env", "env_file_encoding": "utf-8"}

    # Auth — opt-in API key (enables auth when set)
    api_key: str | None = None

    # Server
    host: str = "127.0.0.1"
    port: int = 8002
    reload: bool = False
    workers: int = 1
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174"

    # LLM
    llm_provider: str = "google"
    llm_model_id: str = "gemini-2.5-flash"
    llm_api_key: str = ""  # PIPELINE_LLM_API_KEY or GOOGLE_API_KEY

    # Concurrency — free tier: 5 req/min, 20 req/day
    # Paid tier: much higher. Adjust via PIPELINE_LLM_MAX_CONCURRENT
    llm_max_concurrent: int = 2
    llm_retry_delay: float = 15.0  # base retry delay (matches Gemini 429 retryDelay)
    llm_max_retries: int = 5  # more retries for rate-limited APIs
    llm_debug_mode: bool = True  # Agno agent debug logging

    # Ingestion — chunking
    chunk_token_threshold: int = 8000  # papers below this take the unchunked single-call path
    chunk_similarity_threshold: float = (
        0.55  # Tier 2: adjacent-paragraph cosine similarity split point
    )

    # Persistence
    jobs_dir: str = "./jobs"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_embedding_model: str = "gemini-embedding-001"

    # Restate
    restate_ingress_url: str = "http://localhost:8080"

    # WebSocket
    ws_path: str = "/ws"

    # Judge gate — opt-in post-aggregation quality gate (unset = disabled,
    # matches api_key's opt-in-only-when-set convention above)
    judge_gate_url: str | None = None
    judge_gate_timeout: float = 30.0

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
