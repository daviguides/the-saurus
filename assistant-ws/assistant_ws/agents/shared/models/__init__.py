import os

from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat

from assistant_ws.config import settings

# Propagate AT_LLM_API_KEY to provider-specific env vars for Agno SDK
if settings.llm_api_key:
    if settings.llm_provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = settings.llm_api_key
    elif settings.llm_provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = settings.llm_api_key


def create_model():
    if settings.llm_provider == "openai":
        return OpenAIChat(
            id=settings.llm_model_id,
            api_key=settings.llm_api_key,
        )

    return Claude(
        id=settings.llm_model_id,
        api_key=settings.llm_api_key,
    )
