"""Pydantic models for Socket.IO events and YAML test cases."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Socket.IO event payloads (mirror assistant-ws schemas)
# ---------------------------------------------------------------------------


class TokenEvent(BaseModel):
    content: str


class StepEvent(BaseModel):
    step: str
    agent: str | None = None
    tool: str | None = None


class DoneEvent(BaseModel):
    metrics: dict


class ErrorEvent(BaseModel):
    message: str


class ChatResponse(BaseModel):
    """Aggregated result of a single send_message call."""

    content: str = ""
    steps: list[StepEvent] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    elapsed_ms: float = 0.0


# ---------------------------------------------------------------------------
# YAML test-case schema
# ---------------------------------------------------------------------------


class TestStep(BaseModel):
    message: str
    wait_for_done: bool = True
    timeout_seconds: float = 60.0
    expect_no_error: bool = True
    expect_content_contains: list[str] = Field(default_factory=list)
    expect_content_not_contains: list[str] = Field(default_factory=list)
    expect_steps_min: int = 0
    expect_tools: list[str] = Field(default_factory=list)


class TestCase(BaseModel):
    name: str
    description: str = ""
    timeout_seconds: float = 60.0
    new_session: bool = True
    steps: list[TestStep]
