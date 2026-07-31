"""Tests for the post-aggregation judge-gate HTTP client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pipeline.agents.judge_gate import score_review

REVIEW = {
    "title": "A Review",
    "abstract": "This review covers X.",
    "sections": [{"label": "Theme A", "content": "Section content [1]."}],
}
CLAIMS = [{"text": "Claim text."}]


def _mock_response(json_data: dict) -> MagicMock:
    response = MagicMock(spec=httpx.Response)
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    return response


@pytest.mark.asyncio
async def test_score_review_skipped_when_url_unset():
    with patch("pipeline.agents.judge_gate.settings") as mock_settings:
        mock_settings.judge_gate_url = None
        result = await score_review(REVIEW, CLAIMS)
    assert result.verdict == "pass"
    assert result.scores == {}


@pytest.mark.asyncio
async def test_score_review_pass():
    body = {
        "faithfulness": {"score": 0.9, "passed": True},
        "citation_accuracy": {"score": 0.85, "passed": True},
        "verdict": "pass",
    }
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=_mock_response(body))
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with (
        patch("pipeline.agents.judge_gate.settings") as mock_settings,
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.judge_gate_url = "http://judge-gate:8013"
        mock_settings.judge_gate_timeout = 30.0
        result = await score_review(REVIEW, CLAIMS)

    assert result.verdict == "pass"
    assert result.scores["faithfulness"] == 0.9


@pytest.mark.asyncio
async def test_score_review_quarantine_on_metric_fail():
    body = {
        "faithfulness": {"score": 0.2, "passed": False},
        "citation_accuracy": {"score": 0.85, "passed": True},
        "verdict": "quarantine",
    }
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=_mock_response(body))
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with (
        patch("pipeline.agents.judge_gate.settings") as mock_settings,
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.judge_gate_url = "http://judge-gate:8013"
        mock_settings.judge_gate_timeout = 30.0
        result = await score_review(REVIEW, CLAIMS)

    assert result.verdict == "quarantine"
    assert "faithfulness" in result.reason


@pytest.mark.asyncio
async def test_score_review_quarantine_on_unreachable():
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with (
        patch("pipeline.agents.judge_gate.settings") as mock_settings,
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.judge_gate_url = "http://judge-gate:8013"
        mock_settings.judge_gate_timeout = 30.0
        result = await score_review(REVIEW, CLAIMS)

    assert result.verdict == "quarantine"
    assert "unreachable" in result.reason
