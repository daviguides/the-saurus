"""Config-driven LLM judge factory.

Centralizes judge-model selection for both DeepEval (test suite) and
RAGAS (production scoring) consumers behind one env-var-driven provider
choice, so the judge family stays independent of the model families the
pipeline (Gemini) and assistant (OpenAI) use for generation — avoiding
same-family self-preference bias (design doc §8.1 Use 1).

Default is Anthropic: the only family independent of both generators.
"""

import os

EVAL_JUDGE_PROVIDER = os.environ.get("EVAL_JUDGE_PROVIDER", "anthropic")
EVAL_JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", "claude-haiku-4-5-20251001")

EVAL_EMBEDDING_PROVIDER = os.environ.get("EVAL_EMBEDDING_PROVIDER", "google")
EVAL_EMBEDDING_MODEL = os.environ.get("EVAL_EMBEDDING_MODEL", "text-embedding-004")

_GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", os.environ.get("PIPELINE_LLM_API_KEY", ""))
_ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
_OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


def create_deepeval_judge(provider: str | None = None, model: str | None = None):
    """Create a DeepEval judge model for the configured provider.

    Args:
        provider: Override the configured provider ("anthropic", "openai",
            "google"). Defaults to EVAL_JUDGE_PROVIDER.
        model: Override the configured model name. Defaults to
            EVAL_JUDGE_MODEL (ignored when provider is "google", which
            keeps its own historical default).

    Returns:
        A deepeval.models.DeepEvalBaseLLM instance.

    Raises:
        ValueError: If provider is not one of the supported families.
    """
    provider = provider or EVAL_JUDGE_PROVIDER

    if provider == "anthropic":
        from deepeval.models import AnthropicModel

        return AnthropicModel(model=model or EVAL_JUDGE_MODEL, api_key=_ANTHROPIC_API_KEY)

    if provider == "openai":
        from deepeval.models import GPTModel

        return GPTModel(model=model or EVAL_JUDGE_MODEL, api_key=_OPENAI_API_KEY)

    if provider == "google":
        from deepeval.models import GeminiModel

        return GeminiModel(model=model or "gemini-2.5-flash", api_key=_GOOGLE_API_KEY)

    raise ValueError(f"Unsupported EVAL_JUDGE_PROVIDER: {provider!r}")


def create_ragas_judge(provider: str | None = None, model: str | None = None):
    """Create a RAGAS judge LLM for the configured provider.

    Args:
        provider: Override the configured provider ("anthropic", "openai",
            "google"). Defaults to EVAL_JUDGE_PROVIDER.
        model: Override the configured model name. Defaults to
            EVAL_JUDGE_MODEL (ignored when provider is "google", which
            keeps its own historical default).

    Returns:
        A ragas InstructorBaseRagasLLM instance from llm_factory.

    Raises:
        ValueError: If provider is not one of the supported families.
    """
    from ragas.llms import llm_factory

    provider = provider or EVAL_JUDGE_PROVIDER

    if provider == "anthropic":
        from anthropic import Anthropic

        client = Anthropic(api_key=_ANTHROPIC_API_KEY)
        return llm_factory(model or EVAL_JUDGE_MODEL, provider="anthropic", client=client)

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=_OPENAI_API_KEY)
        return llm_factory(model or EVAL_JUDGE_MODEL, provider="openai", client=client)

    if provider == "google":
        from google import genai

        client = genai.Client(api_key=_GOOGLE_API_KEY)
        return llm_factory(model or "gemini-2.5-flash", provider="google", client=client)

    raise ValueError(f"Unsupported EVAL_JUDGE_PROVIDER: {provider!r}")


def create_ragas_embeddings(provider: str | None = None, model: str | None = None):
    """Create a RAGAS embeddings instance for the configured provider.

    Args:
        provider: Override the configured provider ("google" only, today).
            Defaults to EVAL_EMBEDDING_PROVIDER.
        model: Override the configured model name. Defaults to
            EVAL_EMBEDDING_MODEL.

    Returns:
        A ragas BaseRagasEmbedding instance from embedding_factory.

    Raises:
        ValueError: If provider is not one of the supported families.
    """
    from ragas.embeddings import embedding_factory

    provider = provider or EVAL_EMBEDDING_PROVIDER

    if provider == "google":
        from google import genai

        client = genai.Client(api_key=_GOOGLE_API_KEY)
        return embedding_factory("google", model or EVAL_EMBEDDING_MODEL, client=client)

    raise ValueError(f"Unsupported EVAL_EMBEDDING_PROVIDER: {provider!r}")
