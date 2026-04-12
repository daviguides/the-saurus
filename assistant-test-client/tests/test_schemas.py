"""Tests for Pydantic schemas and YAML test case parsing."""

from pathlib import Path

import pytest
import yaml

from assistant_test_client.schemas import (
    ChatResponse,
    DoneEvent,
    ErrorEvent,
    StepEvent,
    TestCase,
    TestStep,
    TokenEvent,
)

CASES_DIR = Path(__file__).resolve().parent.parent / "data" / "cases"


# ---------------------------------------------------------------------------
# Event models
# ---------------------------------------------------------------------------


class TestTokenEvent:
    def test_basic(self):
        evt = TokenEvent(content="hello")
        assert evt.content == "hello"

    def test_empty_content(self):
        evt = TokenEvent(content="")
        assert evt.content == ""


class TestStepEvent:
    def test_full(self):
        evt = StepEvent(step="Loading theme map...", agent="PapersAgent", tool="get_theme_map")
        assert evt.step == "Loading theme map..."
        assert evt.agent == "PapersAgent"
        assert evt.tool == "get_theme_map"

    def test_minimal(self):
        evt = StepEvent(step="Thinking...")
        assert evt.agent is None
        assert evt.tool is None


class TestDoneEvent:
    def test_with_metrics(self):
        evt = DoneEvent(metrics={"elapsed_time_ms": 1234})
        assert evt.metrics["elapsed_time_ms"] == 1234

    def test_empty_metrics(self):
        evt = DoneEvent(metrics={})
        assert evt.metrics == {}


class TestErrorEvent:
    def test_basic(self):
        evt = ErrorEvent(message="something went wrong")
        assert evt.message == "something went wrong"


class TestChatResponse:
    def test_defaults(self):
        resp = ChatResponse()
        assert resp.content == ""
        assert resp.steps == []
        assert resp.metrics == {}
        assert resp.elapsed_ms == 0.0

    def test_populated(self):
        resp = ChatResponse(
            content="Hello!",
            steps=[StepEvent(step="thinking")],
            metrics={"elapsed_time_ms": 500},
            elapsed_ms=512.3,
        )
        assert resp.content == "Hello!"
        assert len(resp.steps) == 1
        assert resp.elapsed_ms == 512.3


# ---------------------------------------------------------------------------
# Test case schema
# ---------------------------------------------------------------------------


class TestTestStep:
    def test_defaults(self):
        step = TestStep(message="hi")
        assert step.wait_for_done is True
        assert step.timeout_seconds == 60.0
        assert step.expect_no_error is True
        assert step.expect_content_contains == []
        assert step.expect_content_not_contains == []
        assert step.expect_steps_min == 0
        assert step.expect_tools == []

    def test_full(self):
        step = TestStep(
            message="What themes?",
            expect_content_contains=["theme"],
            expect_tools=["get_theme_map"],
            expect_steps_min=1,
        )
        assert step.expect_tools == ["get_theme_map"]


class TestTestCase:
    def test_minimal(self):
        case = TestCase(name="test", steps=[TestStep(message="hi")])
        assert case.new_session is True
        assert case.timeout_seconds == 60.0

    def test_full(self):
        case = TestCase(
            name="Full Test",
            description="A complete test",
            timeout_seconds=120,
            new_session=False,
            steps=[
                TestStep(message="first"),
                TestStep(message="second"),
            ],
        )
        assert len(case.steps) == 2
        assert case.new_session is False


# ---------------------------------------------------------------------------
# YAML case files parse correctly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_file",
    list(CASES_DIR.glob("*.yaml")),
    ids=lambda p: p.stem,
)
def test_yaml_case_parses(case_file: Path):
    data = yaml.safe_load(case_file.read_text())
    case = TestCase(**data)
    assert case.name
    assert len(case.steps) > 0
