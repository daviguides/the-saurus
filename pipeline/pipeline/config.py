from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "PIPELINE_", "env_file": ".env", "env_file_encoding": "utf-8"}

    # Server
    host: str = "0.0.0.0"
    port: int = 8002
    reload: bool = True
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

    # Persistence
    jobs_dir: str = "./jobs"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    qdrant_embedding_dimension: int = 384

    # WebSocket
    ws_path: str = "/ws"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
