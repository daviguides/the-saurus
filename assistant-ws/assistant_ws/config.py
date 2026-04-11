from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "AT_"}

    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    reload: bool = True
    workers: int = 1
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174"

    # LLM
    llm_provider: str = "anthropic"  # anthropic | openai
    llm_model_id: str = "claude-sonnet-4-20250514"
    llm_api_key: str = ""

    # MCP Servers
    mcp_papers_url: str = "http://127.0.0.1:8012/mcp"
    mcp_timeout_seconds: int = 30
    mcp_max_retries: int = 5

    # Session
    session_ttl_minutes: int = 60

    # Observability
    langfuse_enabled: bool = False
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
