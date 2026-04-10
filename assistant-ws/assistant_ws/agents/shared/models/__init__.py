from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat

from assistant_ws.config import settings


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
