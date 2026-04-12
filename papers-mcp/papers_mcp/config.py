import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Collection names — must match pipeline.core.qdrant constants.
PAPER_THEMES = "paper_themes"
PAPER_CLAIMS = "paper_claims"
THEME_MAP = "theme_map"
THEME_REVIEWS = "theme_reviews"
LITERATURE_REVIEW = "literature_review"


class RetrievalSettings(BaseSettings):
    model_config = {"env_prefix": "PAPERS_", "env_file": ".env", "env_file_encoding": "utf-8"}

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    # Embeddings (Gemini API via Agno GeminiEmbedder)
    embedding_model: str = "gemini-embedding-001"
    embedding_api_key: str = ""  # PAPERS_EMBEDDING_API_KEY (Google API key)
    embedding_timeout: float = 30.0  # seconds

    # Retrieval
    min_score_threshold: float = 0.3
    default_top_k: int = 10

    # MCP Server
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8012

    @model_validator(mode="after")
    def _validate_api_key(self) -> "RetrievalSettings":
        if not self.embedding_api_key:
            logger.warning(
                "PAPERS_EMBEDDING_API_KEY is not set; "
                "embedding-based tools (search_claims) will fail."
            )
        return self


settings = RetrievalSettings()
