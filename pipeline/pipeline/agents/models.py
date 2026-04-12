"""LLM model factory for pipeline agents."""

from __future__ import annotations

import asyncio

from agno.models.google import Gemini

from pipeline.config import settings

# Semaphore to control concurrent LLM calls across all agents.
# Protects against rate limits and allows provider swap later.
llm_semaphore = asyncio.Semaphore(settings.llm_max_concurrent)


def create_model() -> Gemini:
    """Create an Agno Gemini model instance from pipeline settings."""
    # S3: Pass API key directly to Gemini constructor instead of setting env var
    return Gemini(id=settings.llm_model_id, api_key=settings.llm_api_key or None)
