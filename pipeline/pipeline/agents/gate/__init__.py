"""Colang topic gate: reject non-scientific PDFs before the analysis LLM call."""

from .rails import TopicGateResult, evaluate_topic_gate

__all__ = ["TopicGateResult", "evaluate_topic_gate"]
