"""Tests for the runtime toxic-content gate's HTTP client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from pipeline.agents.toxic_gate import check_toxicity

REVIEW = {
    "title": "A Review",
    "abstract": "This review covers X.",
    "sections": [{"label": "Theme A", "content": "Section content."}],
}


def _mock_response(json_data: dict) -> MagicMock:
    response = MagicMock(spec=httpx.Response)
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    return response


def _mock_client(*responses: MagicMock) -> AsyncMock:
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=list(responses))
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    return mock_client


@pytest.mark.asyncio
async def test_check_toxicity_skipped_when_url_unset():
    with patch("pipeline.agents.toxic_gate.settings") as mock_settings:
        mock_settings.toxic_gate_url = None
        result = await check_toxicity(REVIEW)
    assert result.verdict == "pass"
    assert result.score is None


@pytest.mark.asyncio
async def test_check_toxicity_pass_makes_one_call():
    mock_client = _mock_client(_mock_response({"score": 0.0, "passed": True}))

    with (
        patch("pipeline.agents.toxic_gate.settings") as mock_settings,
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.toxic_gate_url = "http://judge-gate:8013"
        mock_settings.toxic_gate_timeout = 30.0
        result = await check_toxicity(REVIEW)

    assert result.verdict == "pass"
    assert result.score == 0.0
    assert mock_client.post.call_count == 1


@pytest.mark.asyncio
async def test_check_toxicity_quarantine_names_failed_field():
    # Combined check fails, then decompose: title ok, abstract ok, section fails.
    mock_client = _mock_client(
        _mock_response({"score": 0.9, "passed": False}),  # combined
        _mock_response({"score": 0.0, "passed": True}),  # title
        _mock_response({"score": 0.0, "passed": True}),  # abstract
        _mock_response({"score": 0.9, "passed": False}),  # section
    )

    with (
        patch("pipeline.agents.toxic_gate.settings") as mock_settings,
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.toxic_gate_url = "http://judge-gate:8013"
        mock_settings.toxic_gate_timeout = 30.0
        result = await check_toxicity(REVIEW)

    assert result.verdict == "quarantine"
    assert "Theme A" in result.reason
    assert "title" not in result.reason
    assert "abstract" not in result.reason
    assert mock_client.post.call_count == 4


@pytest.mark.asyncio
async def test_check_toxicity_quarantine_on_unreachable():
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with (
        patch("pipeline.agents.toxic_gate.settings") as mock_settings,
        patch("httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.toxic_gate_url = "http://judge-gate:8013"
        mock_settings.toxic_gate_timeout = 30.0
        result = await check_toxicity(REVIEW)

    assert result.verdict == "quarantine"
    assert "unreachable" in result.reason
