"""Tests for the standalone spaCy entity extractor."""

from pipeline.core.entities import extract_entities


def test_extract_entities_finds_named_entity() -> None:
    entities = extract_entities("The trial took place in Boston, Massachusetts.")

    assert any("boston" in e for e in entities)


def test_extract_entities_normalizes_case_and_whitespace() -> None:
    entities = extract_entities("Correspondence should be addressed to Dr. Jane Rodriguez.")

    assert all(e == e.lower().strip() for e in entities)


def test_extract_entities_empty_on_entity_free_text() -> None:
    entities = extract_entities("Study of biological rhythms and circadian cycles.")

    assert entities == set()
