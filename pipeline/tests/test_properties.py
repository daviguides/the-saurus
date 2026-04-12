"""Property-based tests for pipeline invariants."""

from datetime import UTC, datetime

import pytest
from hypothesis import given, settings as hsettings
from hypothesis import strategies as st
from pydantic import ValidationError

from pipeline.agents.parsing import estimate_tokens


# --- Token estimation ---


@pytest.mark.property
@given(st.text(max_size=100_000))
def test_estimate_tokens_never_negative(text: str) -> None:
    """Token count is always non-negative."""
    assert estimate_tokens(text) >= 0


@pytest.mark.property
@given(st.text(min_size=4, max_size=1000))
def test_estimate_tokens_less_than_char_count(text: str) -> None:
    """Token count is always less than or equal to character count."""
    assert estimate_tokens(text) <= len(text)


@pytest.mark.property
@given(st.text(max_size=500), st.text(max_size=500))
def test_estimate_tokens_additive_bound(a: str, b: str) -> None:
    """Token estimate of concatenation is at most sum of parts."""
    assert estimate_tokens(a + b) <= estimate_tokens(a) + estimate_tokens(b) + 1


@pytest.mark.property
@given(st.text(max_size=0))
def test_estimate_tokens_empty_string_is_zero(text: str) -> None:
    """Empty string yields zero tokens."""
    assert estimate_tokens(text) == 0


# --- Pydantic model validation: ClaimPosition ---


@pytest.mark.property
@given(
    page=st.integers(min_value=1, max_value=1000),
    paragraph=st.integers(min_value=1, max_value=100),
)
def test_claim_position_accepts_positive_values(page: int, paragraph: int) -> None:
    """ClaimPosition accepts any positive page and paragraph."""
    from pipeline.agents.paper_analyzer import ClaimPosition

    pos = ClaimPosition(page=page, paragraph=paragraph)
    assert pos.page == page
    assert pos.paragraph == paragraph


@pytest.mark.property
@given(
    page=st.integers(min_value=-1000, max_value=1000),
    paragraph=st.integers(min_value=-1000, max_value=1000),
)
def test_claim_position_roundtrips_through_json(page: int, paragraph: int) -> None:
    """ClaimPosition serializes to JSON and back without data loss."""
    from pipeline.agents.paper_analyzer import ClaimPosition

    pos = ClaimPosition(page=page, paragraph=paragraph)
    roundtripped = ClaimPosition.model_validate_json(pos.model_dump_json())
    assert roundtripped.page == page
    assert roundtripped.paragraph == paragraph


# --- Pydantic model validation: ExtractedClaim ---


@pytest.mark.property
@given(
    text=st.text(min_size=1, max_size=200),
    deep=st.text(min_size=1, max_size=200),
    summary=st.text(min_size=1, max_size=200),
    page=st.integers(min_value=1, max_value=500),
    paragraph=st.integers(min_value=1, max_value=50),
)
def test_extracted_claim_construction(
    text: str, deep: str, summary: str, page: int, paragraph: int,
) -> None:
    """ExtractedClaim accepts valid string fields and a position."""
    from pipeline.agents.paper_analyzer import ClaimPosition, ExtractedClaim

    claim = ExtractedClaim(
        text=text,
        position=ClaimPosition(page=page, paragraph=paragraph),
        deep=deep,
        summary=summary,
    )
    assert claim.text == text
    assert claim.summary == summary
    assert claim.position.page == page


# --- Pydantic model validation: ThemeWithClaims ---


@pytest.mark.property
@given(
    name=st.text(min_size=1, max_size=100),
    description=st.text(min_size=1, max_size=300),
    n_claims=st.integers(min_value=1, max_value=5),
)
@hsettings(max_examples=30)
def test_theme_with_claims_requires_non_empty_lists(
    name: str, description: str, n_claims: int,
) -> None:
    """ThemeWithClaims requires at least one position and one claim."""
    from pipeline.agents.paper_analyzer import (
        ClaimPosition,
        ExtractedClaim,
        ThemeWithClaims,
    )

    positions = [ClaimPosition(page=i + 1, paragraph=1) for i in range(n_claims)]
    claims = [
        ExtractedClaim(
            text=f"claim {i}",
            position=ClaimPosition(page=i + 1, paragraph=1),
            deep="deep",
            summary="summary",
        )
        for i in range(n_claims)
    ]
    theme = ThemeWithClaims(
        name=name, description=description, positions=positions, claims=claims,
    )
    assert len(theme.claims) == n_claims
    assert len(theme.positions) == n_claims


@pytest.mark.property
def test_theme_with_claims_rejects_empty_claims() -> None:
    """ThemeWithClaims rejects empty claims list."""
    from pipeline.agents.paper_analyzer import ClaimPosition, ThemeWithClaims

    with pytest.raises(ValidationError):
        ThemeWithClaims(
            name="test",
            description="test",
            positions=[ClaimPosition(page=1, paragraph=1)],
            claims=[],
        )


@pytest.mark.property
def test_theme_with_claims_rejects_empty_positions() -> None:
    """ThemeWithClaims rejects empty positions list."""
    from pipeline.agents.paper_analyzer import (
        ClaimPosition,
        ExtractedClaim,
        ThemeWithClaims,
    )

    with pytest.raises(ValidationError):
        ThemeWithClaims(
            name="test",
            description="test",
            positions=[],
            claims=[
                ExtractedClaim(
                    text="c", position=ClaimPosition(page=1, paragraph=1),
                    deep="d", summary="s",
                )
            ],
        )


# --- Event model ---


@pytest.mark.property
@given(
    event_type=st.sampled_from([
        "job_created", "job_started", "job_completed", "job_failed",
        "stage_started", "stage_completed", "stage_failed",
        "paper_ingested", "paper_processed", "paper_analyzed",
        "theme_extracted", "theme_deduplicated", "claim_extracted",
        "review_generated",
        "agent_started", "agent_tool_call", "agent_tool_result",
        "agent_content", "agent_completed", "agent_error",
    ]),
)
def test_event_type_is_valid_enum(event_type: str) -> None:
    """All expected event type strings are valid EventType values."""
    from pipeline.core.events import EventType

    assert event_type in [e.value for e in EventType]


@pytest.mark.property
@given(
    event_type=st.sampled_from([
        "job_created", "job_started", "job_completed", "job_failed",
    ]),
    job_id=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
)
def test_event_roundtrips_through_json(event_type: str, job_id: str) -> None:
    """Event model serializes to JSON and back without data loss."""
    from pipeline.core.events import Event

    event = Event(event_type=event_type, job_id=job_id, payload={"key": "value"})
    roundtripped = Event.model_validate_json(event.model_dump_json())
    assert roundtripped.event_type == event_type
    assert roundtripped.job_id == job_id
    assert roundtripped.payload == {"key": "value"}


# --- JobStatus model ---


@pytest.mark.property
@given(
    progress=st.floats(min_value=0.0, max_value=1.0),
    paper_count=st.integers(min_value=0, max_value=1000),
)
def test_job_status_progress_bounded(progress: float, paper_count: int) -> None:
    """JobStatus accepts progress between 0 and 1."""
    from pipeline.core.models import JobState, JobStatus

    now = datetime.now(UTC)
    status = JobStatus(
        job_id="test",
        status=JobState.RUNNING,
        stage="paper_analysis",
        progress=progress,
        paper_count=paper_count,
        created_at=now,
        updated_at=now,
    )
    assert 0.0 <= status.progress <= 1.0


@pytest.mark.property
@given(state=st.sampled_from(["pending", "running", "completed", "failed"]))
def test_job_state_values_are_valid(state: str) -> None:
    """All expected state strings are valid JobState values."""
    from pipeline.core.models import JobState

    assert state in [s.value for s in JobState]


@pytest.mark.property
@given(
    job_id=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
    state=st.sampled_from(["pending", "running", "completed", "failed"]),
    stage=st.text(max_size=30),
)
def test_job_status_roundtrips_through_json(job_id: str, state: str, stage: str) -> None:
    """JobStatus serializes to JSON and back without data loss."""
    from pipeline.core.models import JobState, JobStatus

    now = datetime.now(UTC)
    status = JobStatus(
        job_id=job_id,
        status=JobState(state),
        stage=stage,
        progress=0.5,
        paper_count=3,
        created_at=now,
        updated_at=now,
    )
    roundtripped = JobStatus.model_validate_json(status.model_dump_json())
    assert roundtripped.job_id == job_id
    assert roundtripped.status == state
    assert roundtripped.stage == stage


# --- ThemeGroup (theme_dedup) ---


@pytest.mark.property
@given(
    canonical_name=st.text(min_size=1, max_size=100),
    description=st.text(min_size=1, max_size=300),
    n_members=st.integers(min_value=1, max_value=20),
)
def test_theme_group_requires_non_empty_members(
    canonical_name: str, description: str, n_members: int,
) -> None:
    """ThemeGroup requires at least one member index."""
    from pipeline.agents.theme_dedup import ThemeGroup

    group = ThemeGroup(
        canonical_name=canonical_name,
        description=description,
        member_indices=list(range(n_members)),
    )
    assert len(group.member_indices) == n_members


@pytest.mark.property
def test_theme_group_rejects_empty_members() -> None:
    """ThemeGroup rejects empty member_indices list."""
    from pipeline.agents.theme_dedup import ThemeGroup

    with pytest.raises(ValidationError):
        ThemeGroup(
            canonical_name="test",
            description="test",
            member_indices=[],
        )


# --- AggregatorResult ---


@pytest.mark.property
@given(
    title=st.text(min_size=1, max_size=200),
    abstract=st.text(min_size=1, max_size=500),
)
@hsettings(max_examples=30)
def test_aggregator_result_requires_non_empty_fields(title: str, abstract: str) -> None:
    """AggregatorResult requires non-empty title, abstract, and sections."""
    from pipeline.agents.aggregator import AggregatorResult, ReviewSection

    result = AggregatorResult(
        title=title,
        abstract=abstract,
        sections=[
            ReviewSection(
                theme_id="t1", label="Label", content="Some content here.",
            )
        ],
    )
    assert result.title == title
    assert result.abstract == abstract
    assert len(result.sections) >= 1


@pytest.mark.property
def test_aggregator_result_rejects_empty_title() -> None:
    """AggregatorResult rejects empty title."""
    from pipeline.agents.aggregator import AggregatorResult, ReviewSection

    with pytest.raises(ValidationError):
        AggregatorResult(
            title="",
            abstract="Some abstract.",
            sections=[
                ReviewSection(
                    theme_id="t1", label="Label", content="Content.",
                )
            ],
        )


@pytest.mark.property
def test_aggregator_result_rejects_empty_sections() -> None:
    """AggregatorResult rejects empty sections list."""
    from pipeline.agents.aggregator import AggregatorResult

    with pytest.raises(ValidationError):
        AggregatorResult(
            title="Title",
            abstract="Abstract.",
            sections=[],
        )


# --- ReviewCitation ---


@pytest.mark.property
@given(
    ref_number=st.integers(min_value=1, max_value=1000),
    claim_id=st.text(min_size=1, max_size=50),
    paper_id=st.text(min_size=1, max_size=50),
)
def test_review_citation_construction(ref_number: int, claim_id: str, paper_id: str) -> None:
    """ReviewCitation accepts valid ref_number, claim_id, paper_id."""
    from pipeline.agents.aggregator import ReviewCitation

    citation = ReviewCitation(
        ref_number=ref_number, claim_id=claim_id, paper_id=paper_id,
    )
    assert citation.ref_number == ref_number
    assert citation.claim_id == claim_id
    assert citation.paper_id == paper_id


# --- PaperEntry model ---


@pytest.mark.property
@given(
    paper_id=st.text(min_size=1, max_size=50),
    filename=st.text(min_size=1, max_size=100),
    title=st.text(max_size=200),
    page_count=st.integers(min_value=0, max_value=10000),
)
def test_paper_entry_roundtrips_through_json(
    paper_id: str, filename: str, title: str, page_count: int,
) -> None:
    """PaperEntry serializes to JSON and back without data loss."""
    from pipeline.core.models import PaperEntry

    entry = PaperEntry(
        paper_id=paper_id,
        filename=filename,
        title=title,
        page_count=page_count,
    )
    roundtripped = PaperEntry.model_validate_json(entry.model_dump_json())
    assert roundtripped.paper_id == paper_id
    assert roundtripped.filename == filename
    assert roundtripped.page_count == page_count
