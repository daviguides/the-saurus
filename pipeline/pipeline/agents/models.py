"""LLM model factory for pipeline agents."""

from __future__ import annotations

import asyncio
import os

from agno.models.google import Gemini

from pipeline.config import settings

# Semaphore to control concurrent LLM calls across all agents.
# Protects against rate limits and allows provider swap later.
llm_semaphore = asyncio.Semaphore(settings.llm_max_concurrent)


def create_model() -> Gemini:
    """Create an Agno Gemini model instance from pipeline settings."""
    # Propagate PIPELINE_LLM_API_KEY to GOOGLE_API_KEY for Agno/Gemini SDK
    if settings.llm_api_key and not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = settings.llm_api_key
    return Gemini(id=settings.llm_model_id, api_key=settings.llm_api_key or None)
