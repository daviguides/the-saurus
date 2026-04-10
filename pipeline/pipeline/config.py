from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "PIPELINE_"}

    # Server
    host: str = "0.0.0.0"
    port: int = 8002
    reload: bool = True
    workers: int = 1
    cors_origins: str = "http://localhost:3000"

    # LLM
    llm_provider: str = "anthropic"
    llm_model_id: str = "claude-sonnet-4-20250514"
    llm_api_key: str = ""

    # Persistence
    jobs_dir: str = "./jobs"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "papers"

    # WebSocket
    ws_path: str = "/ws"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
