"""Contract tests for the judge-gate scoring endpoint.

The judge model call itself (deepeval GEval.measure) is mocked — this suite
verifies the endpoint's request/response shape and pass/quarantine mapping,
not deepeval's own scoring correctness (that's already covered by the
existing evals/pipeline/tests/test_review_quality.py suite).
"""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from scoring.judge_gate_service import app

client = TestClient(app)


def _mock_metric(score: float, success: bool) -> MagicMock:
    metric = MagicMock()
    metric.score = score
    metric.success = success
    metric.measure = MagicMock(return_value=None)
    return metric


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_score_review_pass() -> None:
    with (
        patch("scoring.judge_gate_service.create_deepeval_judge", return_value=MagicMock()),
        patch(
            "scoring.judge_gate_service.create_faithfulness_metric",
            return_value=_mock_metric(0.9, True),
        ),
        patch(
            "scoring.judge_gate_service.create_citation_accuracy_metric",
            return_value=_mock_metric(0.85, True),
        ),
    ):
        response = client.post(
            "/score-review",
            json={
                "actual_output": "Review text with [1] citations.",
                "retrieval_context": ["Claim 1 text."],
                "expected_output": "{}",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "pass"
    assert body["faithfulness"]["passed"] is True
    assert body["citation_accuracy"]["passed"] is True


def test_score_review_quarantine_on_faithfulness_fail() -> None:
    with (
        patch("scoring.judge_gate_service.create_deepeval_judge", return_value=MagicMock()),
        patch(
            "scoring.judge_gate_service.create_faithfulness_metric",
            return_value=_mock_metric(0.2, False),
        ),
        patch(
            "scoring.judge_gate_service.create_citation_accuracy_metric",
            return_value=_mock_metric(0.85, True),
        ),
    ):
        response = client.post(
            "/score-review",
            json={"actual_output": "Unfaithful review.", "retrieval_context": [], "expected_output": "{}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "quarantine"
    assert body["faithfulness"]["passed"] is False


def test_score_review_quarantine_on_citation_fail() -> None:
    with (
        patch("scoring.judge_gate_service.create_deepeval_judge", return_value=MagicMock()),
        patch(
            "scoring.judge_gate_service.create_faithfulness_metric",
            return_value=_mock_metric(0.9, True),
        ),
        patch(
            "scoring.judge_gate_service.create_citation_accuracy_metric",
            return_value=_mock_metric(0.1, False),
        ),
    ):
        response = client.post(
            "/score-review",
            json={"actual_output": "Review with bad citations.", "retrieval_context": [], "expected_output": "{}"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "quarantine"
    assert body["citation_accuracy"]["passed"] is False
