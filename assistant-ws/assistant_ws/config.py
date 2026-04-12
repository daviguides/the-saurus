from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "AT_", "env_file": ".env", "env_file_encoding": "utf-8"}

    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    reload: bool = False
    # WARNING: workers > 1 will break in-memory session/team state.
    # Use workers=1 or switch to Redis-backed state before scaling.
    workers: int = 1
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174"

    # Auth — shared secret token for Socket.IO connect auth
    ws_auth_token: str = ""

    # LLM
    llm_provider: str = "openai"  # openai | anthropic
    llm_model_id: str = "gpt-4o-mini"
    llm_api_key: str = ""

    # MCP Servers
    mcp_papers_url: str = "http://127.0.0.1:8012/mcp"
    mcp_timeout_seconds: int = 30
    mcp_max_retries: int = 5
    mcp_connection_ttl_minutes: int = 30

    # Session
    session_ttl_minutes: int = 60

    # Team run timeout (seconds)
    team_run_timeout_seconds: int = 120

    # Max message length (chars)
    max_message_length: int = 10000

    # Observability
    # TODO: Langfuse integration not yet wired. Remove these settings or
    # implement integration when observability is needed.
    langfuse_enabled: bool = False
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
