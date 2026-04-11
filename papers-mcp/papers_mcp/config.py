from pydantic_settings import BaseSettings

# Collection names — must match pipeline.core.qdrant constants.
PAPER_THEMES = "paper_themes"
PAPER_CLAIMS = "paper_claims"
THEME_MAP = "theme_map"
THEME_REVIEWS = "theme_reviews"
LITERATURE_REVIEW = "literature_review"


class RetrievalSettings(BaseSettings):
    model_config = {"env_prefix": "PAPERS_"}

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # Retrieval
    min_score_threshold: float = 0.3
    default_top_k: int = 10

    # MCP Server
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8012


settings = RetrievalSettings()
