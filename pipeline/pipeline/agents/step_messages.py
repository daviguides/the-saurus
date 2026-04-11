"""Human-readable and technical messages for pipeline agent events.

Maps agent names and event types to user-friendly progress messages
with contextual interpolation, plus technical messages for developer view.
Follows the same pattern as AVO's step_messages.py but simplified for
pipeline agents (no MCP tools — pure structured-output agents).
"""

from __future__ import annotations

import re
from typing import Any

# Internal Agno tools that should not be shown to users
INTERNAL_TOOLS: set[str] = {
    "delegate_task_to_member",
    "transfer_task_to_agent",
}

# Agent-specific message templates keyed by (agent_name, event_type).
# Templates support {placeholder} interpolation from context dict.
AGENT_TEMPLATES: dict[tuple[str, str], str] = {
    # PaperAnalyzer
    ("PaperAnalyzer", "agent_started"): "Analyzing '{paper_title}'...",
    ("PaperAnalyzer", "agent_completed"): "Analysis complete",
    ("PaperAnalyzer", "agent_error"): "Analysis failed",
    # ThemeExtractor
    ("ThemeExtractor", "agent_started"): "Extracting themes from '{paper_title}'...",
    ("ThemeExtractor", "agent_completed"): "Theme extraction complete",
    ("ThemeExtractor", "agent_error"): "Theme extraction failed",
    # ClaimExtractor
    ("ClaimExtractor", "agent_started"): "Extracting claims...",
    ("ClaimExtractor", "agent_completed"): "Claim extraction complete",
    ("ClaimExtractor", "agent_error"): "Claim extraction failed",
    # ThemeDedup
    ("ThemeDedup", "agent_started"): "Deduplicating {theme_count} themes across papers...",
    ("ThemeDedup", "agent_completed"): "Deduplication complete",
    ("ThemeDedup", "agent_error"): "Deduplication failed",
    # ThemeReviewer
    ("ThemeReviewer", "agent_started"): "Reviewing themes (batch {batch})...",
    ("ThemeReviewer", "agent_completed"): "Theme review complete",
    ("ThemeReviewer", "agent_error"): "Theme review failed",
    # Aggregator
    ("Aggregator", "agent_started"): "Synthesizing literature review from {theme_count} themes...",
    ("Aggregator", "agent_completed"): "Literature review generated",
    ("Aggregator", "agent_error"): "Aggregation failed",
}

# Fallback messages per event type (when no agent-specific template matches)
EVENT_TYPE_DEFAULTS: dict[str, str] = {
    "agent_started": "Processing...",
    "agent_completed": "Complete",
    "agent_error": "Failed",
    "agent_tool_call": "Gathering information...",
    "agent_tool_result": "Information retrieved",
    "agent_content": "Generating response...",
}


def is_internal_tool(tool_name: str) -> bool:
    """Check if tool is internal Agno machinery (should not show to user)."""
    return tool_name in INTERNAL_TOOLS


def get_step_message(
    event_type: str,
    agent_name: str | None = None,
    context: dict[str, Any] | None = None,
) -> str:
    """Get human-readable message for an agent event.

    Priority:
    1. Agent-specific template with context interpolation
    2. Agent-specific template (fallback — no interpolation)
    3. Event type default
    4. Generic fallback
    """
    if agent_name:
        key = (agent_name, event_type)
        template = AGENT_TEMPLATES.get(key)
        if template:
            if context:
                try:
                    return template.format_map(_SafeFormatDict(context))
                except (KeyError, ValueError):
                    pass
            # Return template with placeholders stripped for readability
            return _strip_placeholders(template)

    return EVENT_TYPE_DEFAULTS.get(event_type, "Processing...")


def get_technical_message(
    event_type: str,
    agent_name: str | None = None,
    payload: dict[str, Any] | None = None,
) -> str:
    """Generate technical message with full details for developer view."""
    parts: list[str] = []

    if agent_name:
        parts.append(f"[{agent_name}]")

    if payload:
        tool_name = payload.get("tool_name")
        if tool_name:
            tool_args = payload.get("tool_args_preview", "")
            if tool_args:
                parts.append(f"{tool_name}({tool_args})")
            else:
                parts.append(tool_name)

            result_len = payload.get("result_len")
            if result_len is not None:
                parts.append(f"→ {result_len} chars")

        elapsed = payload.get("elapsed_ms")
        if elapsed is not None:
            parts.append(f"({elapsed}ms)")

        error = payload.get("error")
        if error:
            parts.append(f"ERROR: {error}")

    if not parts:
        return event_type

    return " ".join(parts)


class _SafeFormatDict(dict):
    """Dict that returns '{key}' for missing keys instead of raising KeyError."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


_PLACEHOLDER_RE = re.compile(r"\s*'?\{[^}]+\}'?\s*")


def _strip_placeholders(template: str) -> str:
    """Remove unfilled {placeholder} tokens from a template for clean display."""
    cleaned = _PLACEHOLDER_RE.sub(" ", template).strip()
    # Collapse multiple spaces and ensure trailing ellipsis
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    if cleaned.endswith("..."):
        return cleaned
    return cleaned.rstrip(".") + "..."
