"""Parse Agno agent responses into Pydantic models.

Agno's result.content may be the Pydantic model directly (structured output worked)
or a raw string (LLM returned text). This helper handles both cases.
"""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def parse_agent_response(raw: object, model_class: type[T]) -> T:
    """Parse an Agno agent response into the expected Pydantic model.

    Handles three cases:
    1. raw is already the expected model (structured output worked)
    2. raw is a string containing JSON (possibly wrapped in markdown code blocks)
    3. raw is a dict-like object
    """
    if isinstance(raw, model_class):
        return raw

    if isinstance(raw, str):
        cleaned = raw.strip()
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
        if json_match:
            cleaned = json_match.group(1).strip()
        return model_class.model_validate_json(cleaned)

    if isinstance(raw, dict):
        return model_class.model_validate(raw)

    # Last resort: try to convert to string and parse
    return model_class.model_validate_json(str(raw))
