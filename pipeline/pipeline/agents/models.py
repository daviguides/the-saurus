"""LLM model factory for pipeline agents."""

from __future__ import annotations

from agno.models.anthropic import Claude

from pipeline.config import settings


def create_model() -> Claude:
    """Create an Agno model instance from pipeline settings."""
    return Claude(id=settings.llm_model_id, api_key=settings.llm_api_key)
