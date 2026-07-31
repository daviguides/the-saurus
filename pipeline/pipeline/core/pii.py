"""Shared Presidio PII scrubbing: one engine, entity scope chosen per caller.

Extracted out of ingestion/extract.py (its sole original caller) so
output-side callers (theme_reviewer.py, aggregator.py) can reuse the same
AnalyzerEngine/AnonymizerEngine instance with a broader entity scope,
mirroring how core/embedding.py was extracted out of core/qdrant.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine

# Input-side scope (extract.py) excludes PERSON to keep author names intact
# for citations. Output-side scope (theme_reviewer.py, aggregator.py) is
# broader — it's checking generated prose for PII that leaked past
# extraction, not preserving attribution.
OUTPUT_SIDE_ENTITIES = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION"]

_analyzer: AnalyzerEngine | None = None
_anonymizer: AnonymizerEngine | None = None


def get_engines() -> tuple[AnalyzerEngine, AnonymizerEngine]:
    """Lazily build and cache the Presidio engines (loads the spaCy model)."""
    global _analyzer, _anonymizer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        from presidio_anonymizer import AnonymizerEngine

        nlp_engine = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
        ).create_engine()
        _analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
        _anonymizer = AnonymizerEngine()
    return _analyzer, _anonymizer


def _operators_for(entities: list[str]) -> dict:
    from presidio_anonymizer.entities import OperatorConfig

    all_operators = {
        "PERSON": OperatorConfig("replace", {"new_value": "[PERSON]"}),
        "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
        "LOCATION": OperatorConfig("replace", {"new_value": "[LOCATION]"}),
    }
    return {e: all_operators[e] for e in entities}


def scrub_text(text: str, entities: list[str]) -> tuple[str, list[str]]:
    """Redact the requested entity types in text. Never raises on detection.

    Returns (scrubbed_text, entity_types_found) — entity_types_found is
    empty when nothing matched, in which case scrubbed_text is the input
    unchanged.
    """
    analyzer, anonymizer = get_engines()
    results = analyzer.analyze(text=text, language="en", entities=entities)
    if not results:
        return text, []
    anonymized = anonymizer.anonymize(
        text=text, analyzer_results=results, operators=_operators_for(entities)
    )
    entity_types = [item.entity_type for item in anonymized.items]
    return anonymized.text, entity_types
