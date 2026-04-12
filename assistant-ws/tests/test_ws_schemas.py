"""Tests for assistant_ws.ws.schemas module."""

import pytest
from pydantic import ValidationError

from assistant_ws.ws.schemas import (
    DoneEvent,
    IncomingMessage,
    ReferenceItem,
    ReferencesEvent,
    StepEvent,
    TokenEvent,
)

# --------------- constants ---------------

SAMPLE_TEXT = "What is photosynthesis?"
SAMPLE_SESSION_ID = "sess-abc-123"
SAMPLE_CONTENT = "Photosynthesis is"
SAMPLE_STEP = "thinking"
SAMPLE_AGENT = "coordinator"
SAMPLE_TOOL = "search_papers"
SAMPLE_TITLE = "A Study on Plants"
SAMPLE_AUTHORS = ["Alice", "Bob"]
SAMPLE_YEAR = 2024
SAMPLE_DOI = "10.1234/example"
SAMPLE_SNIPPET = "Plants convert sunlight..."
SAMPLE_SCORE = 0.95


# --------------- IncomingMessage ---------------


class TestIncomingMessage:
    """Tests for IncomingMessage model."""

    def test_with_text_only(self) -> None:
        """text is required; session_id defaults to None."""
        # Arrange / Act
        msg = IncomingMessage(text=SAMPLE_TEXT)

        # Assert
        assert msg.text == SAMPLE_TEXT
        assert msg.session_id is None

    def test_with_text_and_session_id(self) -> None:
        """Both fields can be provided."""
        # Arrange / Act
        msg = IncomingMessage(
            text=SAMPLE_TEXT,
            session_id=SAMPLE_SESSION_ID,
        )

        # Assert
        assert msg.text == SAMPLE_TEXT
        assert msg.session_id == SAMPLE_SESSION_ID

    def test_missing_text_raises(self) -> None:
        """Omitting required text raises ValidationError."""
        # Arrange / Act / Assert
        with pytest.raises(ValidationError):
            IncomingMessage()  # type: ignore[call-arg]

    def test_serialization_round_trip(self) -> None:
        """model_dump and model_validate are symmetric."""
        # Arrange
        msg = IncomingMessage(
            text=SAMPLE_TEXT,
            session_id=SAMPLE_SESSION_ID,
        )

        # Act
        data = msg.model_dump()
        restored = IncomingMessage.model_validate(data)

        # Assert
        assert restored == msg

    def test_serialization_excludes_none(self) -> None:
        """None session_id is included in dump by default."""
        # Arrange
        msg = IncomingMessage(text=SAMPLE_TEXT)

        # Act
        data = msg.model_dump()

        # Assert
        assert "session_id" in data
        assert data["session_id"] is None


# --------------- TokenEvent ---------------


class TestTokenEvent:
    """Tests for TokenEvent model."""

    def test_with_content(self) -> None:
        """TokenEvent stores content string."""
        # Arrange / Act
        event = TokenEvent(content=SAMPLE_CONTENT)

        # Assert
        assert event.content == SAMPLE_CONTENT

    def test_missing_content_raises(self) -> None:
        """Omitting content raises ValidationError."""
        # Arrange / Act / Assert
        with pytest.raises(ValidationError):
            TokenEvent()  # type: ignore[call-arg]

    def test_empty_content_allowed(self) -> None:
        """Empty string is a valid content value."""
        # Arrange / Act
        event = TokenEvent(content="")

        # Assert
        assert event.content == ""

    def test_serialization(self) -> None:
        """model_dump produces expected dict."""
        # Arrange
        event = TokenEvent(content=SAMPLE_CONTENT)

        # Act
        data = event.model_dump()

        # Assert
        assert data == {"content": SAMPLE_CONTENT}


# --------------- StepEvent ---------------


class TestStepEvent:
    """Tests for StepEvent model."""

    def test_step_only(self) -> None:
        """step is required; agent and tool default to None."""
        # Arrange / Act
        event = StepEvent(step=SAMPLE_STEP)

        # Assert
        assert event.step == SAMPLE_STEP
        assert event.agent is None
        assert event.tool is None

    def test_all_fields(self) -> None:
        """All three fields can be provided."""
        # Arrange / Act
        event = StepEvent(
            step=SAMPLE_STEP,
            agent=SAMPLE_AGENT,
            tool=SAMPLE_TOOL,
        )

        # Assert
        assert event.step == SAMPLE_STEP
        assert event.agent == SAMPLE_AGENT
        assert event.tool == SAMPLE_TOOL

    def test_missing_step_raises(self) -> None:
        """Omitting required step raises ValidationError."""
        # Arrange / Act / Assert
        with pytest.raises(ValidationError):
            StepEvent(agent=SAMPLE_AGENT)  # type: ignore[call-arg]

    def test_serialization_round_trip(self) -> None:
        """Round-trip through dict preserves values."""
        # Arrange
        event = StepEvent(
            step=SAMPLE_STEP,
            agent=SAMPLE_AGENT,
        )

        # Act
        restored = StepEvent.model_validate(event.model_dump())

        # Assert
        assert restored == event


# --------------- DoneEvent ---------------


class TestDoneEvent:
    """Tests for DoneEvent model."""

    def test_with_metrics(self) -> None:
        """DoneEvent stores a metrics dict."""
        # Arrange
        metrics = {"duration_ms": 1200, "tokens": 350}

        # Act
        event = DoneEvent(metrics=metrics)

        # Assert
        assert event.metrics == metrics

    def test_empty_metrics(self) -> None:
        """Empty dict is a valid metrics value."""
        # Arrange / Act
        event = DoneEvent(metrics={})

        # Assert
        assert event.metrics == {}

    def test_missing_metrics_raises(self) -> None:
        """Omitting required metrics raises ValidationError."""
        # Arrange / Act / Assert
        with pytest.raises(ValidationError):
            DoneEvent()  # type: ignore[call-arg]

    def test_serialization(self) -> None:
        """model_dump produces expected dict."""
        # Arrange
        metrics = {"status": "ok"}
        event = DoneEvent(metrics=metrics)

        # Act
        data = event.model_dump()

        # Assert
        assert data == {"metrics": {"status": "ok"}}


# --------------- ReferenceItem ---------------


class TestReferenceItem:
    """Tests for ReferenceItem model."""

    def test_title_only(self) -> None:
        """Only title is required; all others default to None."""
        # Arrange / Act
        ref = ReferenceItem(title=SAMPLE_TITLE)

        # Assert
        assert ref.title == SAMPLE_TITLE
        assert ref.authors is None
        assert ref.year is None
        assert ref.doi is None
        assert ref.snippet is None
        assert ref.score is None

    def test_all_fields(self) -> None:
        """All fields can be provided."""
        # Arrange / Act
        ref = ReferenceItem(
            title=SAMPLE_TITLE,
            authors=SAMPLE_AUTHORS,
            year=SAMPLE_YEAR,
            doi=SAMPLE_DOI,
            snippet=SAMPLE_SNIPPET,
            score=SAMPLE_SCORE,
        )

        # Assert
        assert ref.title == SAMPLE_TITLE
        assert ref.authors == SAMPLE_AUTHORS
        assert ref.year == SAMPLE_YEAR
        assert ref.doi == SAMPLE_DOI
        assert ref.snippet == SAMPLE_SNIPPET
        assert ref.score == SAMPLE_SCORE

    def test_missing_title_raises(self) -> None:
        """Omitting required title raises ValidationError."""
        # Arrange / Act / Assert
        with pytest.raises(ValidationError):
            ReferenceItem(authors=SAMPLE_AUTHORS)  # type: ignore[call-arg]

    def test_serialization_round_trip(self) -> None:
        """Round-trip through dict preserves all values."""
        # Arrange
        ref = ReferenceItem(
            title=SAMPLE_TITLE,
            authors=SAMPLE_AUTHORS,
            year=SAMPLE_YEAR,
            score=SAMPLE_SCORE,
        )

        # Act
        restored = ReferenceItem.model_validate(ref.model_dump())

        # Assert
        assert restored == ref

    def test_empty_authors_list(self) -> None:
        """Empty authors list is valid."""
        # Arrange / Act
        ref = ReferenceItem(title=SAMPLE_TITLE, authors=[])

        # Assert
        assert ref.authors == []


# --------------- ReferencesEvent ---------------


class TestReferencesEvent:
    """Tests for ReferencesEvent model."""

    def test_with_references(self) -> None:
        """ReferencesEvent holds a list of ReferenceItem."""
        # Arrange
        item = ReferenceItem(title=SAMPLE_TITLE)

        # Act
        event = ReferencesEvent(references=[item])

        # Assert
        assert len(event.references) == 1
        assert event.references[0].title == SAMPLE_TITLE

    def test_empty_references(self) -> None:
        """Empty references list is valid."""
        # Arrange / Act
        event = ReferencesEvent(references=[])

        # Assert
        assert event.references == []

    def test_missing_references_raises(self) -> None:
        """Omitting required references raises ValidationError."""
        # Arrange / Act / Assert
        with pytest.raises(ValidationError):
            ReferencesEvent()  # type: ignore[call-arg]

    def test_multiple_references(self) -> None:
        """Multiple references are stored in order."""
        # Arrange
        items = [
            ReferenceItem(title="Paper A"),
            ReferenceItem(title="Paper B"),
            ReferenceItem(title="Paper C"),
        ]

        # Act
        event = ReferencesEvent(references=items)

        # Assert
        titles = [r.title for r in event.references]
        assert titles == ["Paper A", "Paper B", "Paper C"]

    def test_serialization_nested(self) -> None:
        """Serialization preserves nested ReferenceItem data."""
        # Arrange
        item = ReferenceItem(
            title=SAMPLE_TITLE,
            authors=SAMPLE_AUTHORS,
            year=SAMPLE_YEAR,
        )
        event = ReferencesEvent(references=[item])

        # Act
        data = event.model_dump()

        # Assert
        assert len(data["references"]) == 1
        assert data["references"][0]["title"] == SAMPLE_TITLE
        assert data["references"][0]["authors"] == SAMPLE_AUTHORS

    def test_from_raw_dicts(self) -> None:
        """ReferencesEvent can be built from raw dict data."""
        # Arrange
        raw = {
            "references": [
                {"title": "Paper X"},
                {"title": "Paper Y", "year": SAMPLE_YEAR},
            ],
        }

        # Act
        event = ReferencesEvent.model_validate(raw)

        # Assert
        assert len(event.references) == 2
        assert event.references[1].year == SAMPLE_YEAR
