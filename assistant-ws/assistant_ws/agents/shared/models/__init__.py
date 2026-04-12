from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat

from assistant_ws.config import settings

_SUPPORTED_PROVIDERS = {"openai", "anthropic"}


def create_model():
    provider = settings.llm_provider
    if provider not in _SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Unknown LLM provider '{provider}'. "
            f"Supported: {', '.join(sorted(_SUPPORTED_PROVIDERS))}"
        )

    if provider == "openai":
        return OpenAIChat(
            id=settings.llm_model_id,
            api_key=settings.llm_api_key,
        )

    return Claude(
        id=settings.llm_model_id,
        api_key=settings.llm_api_key,
    )
