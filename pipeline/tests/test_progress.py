"""Tests for progress tracker: stage lifecycle and overall progress math."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pipeline.engine.progress import ProgressTracker

# --- Constants ---

JOB_ID = "job-001"
PAPER_COUNT = 3
STAGE_ANALYSIS = "paper_analysis"
STAGE_DEDUP = "theme_dedup"
STAGE_REVIEW = "theme_review"
STAGE_AGGREGATION = "aggregation"
TOTAL_STAGES = 4  # from pipeline.engine.stages


# --- Helpers ---


def _make_tracker(
    job_id: str = JOB_ID,
    paper_count: int = PAPER_COUNT,
) -> tuple[ProgressTracker, AsyncMock, AsyncMock]:
    """Build a ProgressTracker with mocked emitter and write_status.

    Returns:
        Tuple of (tracker, mock_emitter, mock_write_status).
    """
    emitter = AsyncMock()
    jobs_dir = Path("/tmp/test-jobs")

    with patch(
        "pipeline.engine.progress.write_status",
        new_callable=AsyncMock,
    ) as mock_ws:
        tracker = ProgressTracker(
            job_id=job_id,
            jobs_dir=jobs_dir,
            emitter=emitter,
            paper_count=paper_count,
        )

    return tracker, emitter, mock_ws


# --- Stage lifecycle ---


class TestStageStart:
    """Validate stage_start behavior."""

    @pytest.mark.asyncio
    async def test_stage_start_resets_counters(self) -> None:
        """stage_start resets counter to 0 and sets total."""
        # Arrange
        tracker, emitter, _ = _make_tracker()
        total_items = 5

        with patch(
            "pipeline.engine.progress.write_status",
            new_callable=AsyncMock,
        ):
            # Act
            await tracker.stage_start(STAGE_ANALYSIS, total_items)

        # Assert
        assert tracker._stage_counter == 0
        assert tracker._stage_total == total_items

    @pytest.mark.asyncio
    async def test_stage_start_emits_event(self) -> None:
        """stage_start emits STAGE_STARTED event."""
        # Arrange
        tracker, emitter, _ = _make_tracker()
        total_items = 3

        with patch(
            "pipeline.engine.progress.write_status",
            new_callable=AsyncMock,
        ):
            # Act
            await tracker.stage_start(STAGE_ANALYSIS, total_items)

        # Assert
        emitter.emit.assert_called_once()
        call_args = emitter.emit.call_args
        assert call_args[0][1]["stage"] == STAGE_ANALYSIS
        assert call_args[0][1]["total"] == total_items


class TestStageItemDone:
    """Validate stage_item_done increments and emits."""

    @pytest.mark.asyncio
    async def test_increments_counter(self) -> None:
        """stage_item_done increments the stage counter by 1."""
        # Arrange
        tracker, emitter, _ = _make_tracker()

        with patch(
            "pipeline.engine.progress.write_status",
            new_callable=AsyncMock,
        ):
            await tracker.stage_start(STAGE_ANALYSIS, PAPER_COUNT)

            # Act
            await tracker.stage_item_done(
                STAGE_ANALYSIS,
                "paper-1",
            )

        # Assert
        assert tracker._stage_counter == 1

    @pytest.mark.asyncio
    async def test_multiple_items_increment(self) -> None:
        """Multiple stage_item_done calls increment correctly."""
        # Arrange
        tracker, emitter, _ = _make_tracker()
        items_done = 3

        with patch(
            "pipeline.engine.progress.write_status",
            new_callable=AsyncMock,
        ):
            await tracker.stage_start(
                STAGE_ANALYSIS,
                items_done,
            )

            # Act
            for i in range(items_done):
                await tracker.stage_item_done(
                    STAGE_ANALYSIS,
                    f"paper-{i}",
                )

        # Assert
        assert tracker._stage_counter == items_done

    @pytest.mark.asyncio
    async def test_emits_paper_processed_before_last(self) -> None:
        """Emits PAPER_PROCESSED when not the final item."""
        # Arrange
        tracker, emitter, _ = _make_tracker()
        total_items = 2

        with patch(
            "pipeline.engine.progress.write_status",
            new_callable=AsyncMock,
        ):
            await tracker.stage_start(
                STAGE_ANALYSIS,
                total_items,
            )
            emitter.emit.reset_mock()

            # Act
            await tracker.stage_item_done(
                STAGE_ANALYSIS,
                "paper-0",
            )

        # Assert — first item of 2 emits PAPER_PROCESSED
        call_args = emitter.emit.call_args
        from pipeline.core.events import EventType
        assert call_args[0][0] == EventType.PAPER_PROCESSED

    @pytest.mark.asyncio
    async def test_emits_paper_processed_on_last(self) -> None:
        """Emits PAPER_PROCESSED even on the last item (stage_complete handles STAGE_COMPLETED)."""
        # Arrange
        tracker, emitter, _ = _make_tracker()
        total_items = 1

        with patch(
            "pipeline.engine.progress.write_status",
            new_callable=AsyncMock,
        ):
            await tracker.stage_start(
                STAGE_ANALYSIS,
                total_items,
            )
            emitter.emit.reset_mock()

            # Act
            await tracker.stage_item_done(
                STAGE_ANALYSIS,
                "paper-0",
            )

        # Assert — stage_item_done always emits PAPER_PROCESSED, not STAGE_COMPLETED
        call_args = emitter.emit.call_args
        from pipeline.core.events import EventType
        assert call_args[0][0] == EventType.PAPER_PROCESSED


class TestStageComplete:
    """Validate stage_complete finalizes a stage."""

    @pytest.mark.asyncio
    async def test_increments_completed_stages(self) -> None:
        """stage_complete increments the completed stages count."""
        # Arrange
        tracker, emitter, _ = _make_tracker()

        with patch(
            "pipeline.engine.progress.write_status",
            new_callable=AsyncMock,
        ):
            # Act
            await tracker.stage_complete(STAGE_ANALYSIS)

        # Assert
        assert tracker._completed_stages == 1

    @pytest.mark.asyncio
    async def test_resets_stage_counters(self) -> None:
        """stage_complete resets counter and total to zero."""
        # Arrange
        tracker, emitter, _ = _make_tracker()

        with patch(
            "pipeline.engine.progress.write_status",
            new_callable=AsyncMock,
        ):
            await tracker.stage_start(STAGE_ANALYSIS, 5)
            tracker._stage_counter = 5

            # Act
            await tracker.stage_complete(STAGE_ANALYSIS)

        # Assert
        assert tracker._stage_counter == 0
        assert tracker._stage_total == 0

    @pytest.mark.asyncio
    async def test_emits_stage_completed_event(self) -> None:
        """stage_complete emits STAGE_COMPLETED event."""
        # Arrange
        tracker, emitter, _ = _make_tracker()

        with patch(
            "pipeline.engine.progress.write_status",
            new_callable=AsyncMock,
        ):
            # Act
            await tracker.stage_complete(STAGE_ANALYSIS)

        # Assert
        call_args = emitter.emit.call_args
        from pipeline.core.events import EventType
        assert call_args[0][0] == EventType.STAGE_COMPLETED
        assert call_args[0][1]["stage"] == STAGE_ANALYSIS


# --- Overall progress math ---


class TestOverallProgress:
    """Validate _overall_progress calculations."""

    def test_zero_at_start(self) -> None:
        """Progress is 0.0 before any stages complete."""
        # Arrange
        tracker, _, _ = _make_tracker()

        # Act / Assert
        assert tracker._overall_progress() == 0.0

    def test_one_stage_complete(self) -> None:
        """One completed stage = 1/TOTAL_STAGES."""
        # Arrange
        tracker, _, _ = _make_tracker()
        tracker._completed_stages = 1

        # Act
        progress = tracker._overall_progress()

        # Assert
        expected = 1.0 / TOTAL_STAGES
        assert progress == pytest.approx(expected)

    def test_all_stages_complete(self) -> None:
        """All stages completed = 1.0."""
        # Arrange
        tracker, _, _ = _make_tracker()
        tracker._completed_stages = TOTAL_STAGES

        # Act / Assert
        assert tracker._overall_progress() == pytest.approx(1.0)

    def test_mid_stage_progress(self) -> None:
        """Progress accounts for partial stage completion."""
        # Arrange
        tracker, _, _ = _make_tracker()
        tracker._completed_stages = 1
        items_done = 2
        items_total = 4
        tracker._stage_counter = items_done
        tracker._stage_total = items_total

        # Act
        progress = tracker._overall_progress()

        # Assert
        stage_frac = items_done / items_total
        expected = (1 + stage_frac) / TOTAL_STAGES
        assert progress == pytest.approx(expected)

    def test_zero_stage_total_gives_zero_fraction(self) -> None:
        """When stage_total is 0, stage fraction is 0.0."""
        # Arrange
        tracker, _, _ = _make_tracker()
        tracker._completed_stages = 2
        tracker._stage_counter = 0
        tracker._stage_total = 0

        # Act
        progress = tracker._overall_progress()

        # Assert
        expected = 2.0 / TOTAL_STAGES
        assert progress == pytest.approx(expected)

    def test_progress_with_total_stages_zero(self) -> None:
        """If TOTAL_STAGES is 0, progress returns 1.0."""
        # Arrange
        tracker, _, _ = _make_tracker()

        # Act
        with patch(
            "pipeline.engine.progress.TOTAL_STAGES",
            0,
        ):
            progress = tracker._overall_progress()

        # Assert
        assert progress == 1.0

    def test_half_of_second_stage(self) -> None:
        """After 1 complete stage, halfway through 2nd stage."""
        # Arrange
        tracker, _, _ = _make_tracker()
        tracker._completed_stages = 1
        tracker._stage_counter = 5
        tracker._stage_total = 10

        # Act
        progress = tracker._overall_progress()

        # Assert
        expected = (1 + 0.5) / TOTAL_STAGES
        assert progress == pytest.approx(expected)


# --- Full lifecycle integration ---


class TestFullLifecycle:
    """Test a complete stage lifecycle through the tracker."""

    @pytest.mark.asyncio
    async def test_full_stage_lifecycle(self) -> None:
        """Walk through start, item_done x N, complete for one stage."""
        # Arrange
        tracker, emitter, _ = _make_tracker()
        total_items = 2

        with patch(
            "pipeline.engine.progress.write_status",
            new_callable=AsyncMock,
        ):
            # Act
            await tracker.stage_start(
                STAGE_ANALYSIS,
                total_items,
            )
            for i in range(total_items):
                await tracker.stage_item_done(
                    STAGE_ANALYSIS,
                    f"paper-{i}",
                )
            await tracker.stage_complete(STAGE_ANALYSIS)

        # Assert
        assert tracker._completed_stages == 1
        assert tracker._stage_counter == 0
        assert tracker._stage_total == 0

    @pytest.mark.asyncio
    async def test_two_stages_sequential(self) -> None:
        """Two full stages bring progress to 2/TOTAL_STAGES."""
        # Arrange
        tracker, emitter, _ = _make_tracker()

        with patch(
            "pipeline.engine.progress.write_status",
            new_callable=AsyncMock,
        ):
            # Act
            await tracker.stage_start(STAGE_ANALYSIS, 1)
            await tracker.stage_item_done(
                STAGE_ANALYSIS,
                "p1",
            )
            await tracker.stage_complete(STAGE_ANALYSIS)

            await tracker.stage_start(STAGE_DEDUP, 1)
            await tracker.stage_item_done(
                STAGE_DEDUP,
                "dedup-1",
            )
            await tracker.stage_complete(STAGE_DEDUP)

        # Assert
        assert tracker._completed_stages == 2
        expected = 2.0 / TOTAL_STAGES
        assert tracker._overall_progress() == pytest.approx(
            expected,
        )
