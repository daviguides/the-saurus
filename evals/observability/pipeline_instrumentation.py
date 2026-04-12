"""Langfuse instrumentation for the pipeline service."""

import os
import logging

logger = logging.getLogger(__name__)


def init_pipeline_observability():
    """Initialize Langfuse tracing for pipeline Agno agents.

    Instruments all Agno agent calls via OpenLIT and
    Google GenAI calls via OpenInference.

    Environment variables:
        LANGFUSE_PUBLIC_KEY: Langfuse public key
        LANGFUSE_SECRET_KEY: Langfuse secret key
        LANGFUSE_BASE_URL: Langfuse server URL (default: http://localhost:3000)
        LANGFUSE_SAMPLE_RATE: Fraction of traces to capture (default: 1.0)
    """
    try:
        from langfuse import get_client
        import openlit
        from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

        langfuse = get_client()

        if not langfuse.auth_check():
            logger.warning("Langfuse auth check failed, observability disabled")
            return None

        openlit.init(tracer=langfuse._otel_tracer, disable_batch=True)
        GoogleGenAIInstrumentor().instrument()

        logger.info("Pipeline observability initialized (Langfuse + OpenLIT)")
        return langfuse

    except Exception:
        logger.debug("Langfuse not available, observability disabled", exc_info=True)
        return None
