"""Tests for step_messages: human-readable and technical agent event messages."""

from __future__ import annotations

import pytest

from pipeline.agents.step_messages import (
    AGENT_TEMPLATES,
    EVENT_TYPE_DEFAULTS,
    get_step_message,
    get_technical_message,
    is_internal_tool,
)

ALL_AGENTS = [
    "PaperAnalyzer",
    "ThemeDedup",
    "ThemeReviewer",
    "Aggregator",
]


class TestGetStepMessage:
    @pytest.mark.parametrize("agent_name", ALL_AGENTS)
    def test_all_agents_have_started_message(self, agent_name: str):
        msg = get_step_message("agent_started", agent_name)
        # Should not be the generic default
        assert msg != EVENT_TYPE_DEFAULTS["agent_started"]
        assert msg  # non-empty

    @pytest.mark.parametrize("agent_name", ALL_AGENTS)
    def test_all_agents_have_completed_message(self, agent_name: str):
        msg = get_step_message("agent_completed", agent_name)
        assert msg != EVENT_TYPE_DEFAULTS["agent_completed"]
        assert msg

    @pytest.mark.parametrize("agent_name", ALL_AGENTS)
    def test_all_agents_have_error_message(self, agent_name: str):
        msg = get_step_message("agent_error", agent_name)
        assert msg != EVENT_TYPE_DEFAULTS["agent_error"]
        assert msg

    def test_context_interpolation_paper_title(self):
        msg = get_step_message(
            "agent_started", "PaperAnalyzer",
            context={"paper_title": "Quantum Computing Review"},
        )
        assert "Quantum Computing Review" in msg

    def test_context_interpolation_theme_count(self):
        msg = get_step_message(
            "agent_started", "ThemeDedup",
            context={"theme_count": 42},
        )
        assert "42" in msg

    def test_missing_context_uses_fallback(self):
        # PaperAnalyzer template needs paper_title, but we pass empty context
        msg = get_step_message("agent_started", "PaperAnalyzer", context={})
        # Should not raise, should return a clean string
        assert msg
        assert "{paper_title}" not in msg

    def test_no_context_strips_placeholders(self):
        msg = get_step_message("agent_started", "PaperAnalyzer")
        assert "{" not in msg
        assert msg.endswith("...")

    def test_unknown_agent_gets_default(self):
        msg = get_step_message("agent_started", "UnknownAgent")
        assert msg == EVENT_TYPE_DEFAULTS["agent_started"]

    def test_unknown_event_type_gets_generic(self):
        msg = get_step_message("unknown_event", "PaperAnalyzer")
        assert msg == "Processing..."

    def test_no_agent_name_gets_default(self):
        msg = get_step_message("agent_started")
        assert msg == EVENT_TYPE_DEFAULTS["agent_started"]


class TestGetTechnicalMessage:
    def test_agent_name_in_brackets(self):
        msg = get_technical_message("agent_started", "PaperAnalyzer")
        assert "[PaperAnalyzer]" in msg

    def test_tool_name_and_args(self):
        msg = get_technical_message(
            "agent_tool_call", "TestAgent",
            payload={"tool_name": "search", "tool_args_preview": '{"q": "test"}'},
        )
        assert "search" in msg
        assert '{"q": "test"}' in msg

    def test_result_len(self):
        msg = get_technical_message(
            "agent_tool_result", "TestAgent",
            payload={"tool_name": "search", "result_len": 1500},
        )
        assert "1500 chars" in msg

    def test_elapsed_ms(self):
        msg = get_technical_message(
            "agent_completed", "TestAgent",
            payload={"elapsed_ms": 2500},
        )
        assert "2500ms" in msg

    def test_error_in_message(self):
        msg = get_technical_message(
            "agent_error", "TestAgent",
            payload={"error": "Rate limit exceeded"},
        )
        assert "Rate limit exceeded" in msg

    def test_no_payload_returns_event_type(self):
        msg = get_technical_message("agent_started")
        assert msg == "agent_started"

    def test_no_agent_no_payload(self):
        msg = get_technical_message("agent_content")
        assert msg == "agent_content"


class TestIsInternalTool:
    def test_delegate_task_is_internal(self):
        assert is_internal_tool("delegate_task_to_member") is True

    def test_transfer_task_is_internal(self):
        assert is_internal_tool("transfer_task_to_agent") is True

    def test_regular_tool_is_not_internal(self):
        assert is_internal_tool("search_docs") is False

    def test_empty_string_is_not_internal(self):
        assert is_internal_tool("") is False
