"""Tests for the shared Presidio PII scrub module (core/pii.py)."""

from __future__ import annotations

from pipeline.core import pii


class TestGetEngines:
    def test_returns_cached_singleton(self) -> None:
        analyzer1, anonymizer1 = pii.get_engines()
        analyzer2, anonymizer2 = pii.get_engines()
        assert analyzer1 is analyzer2
        assert anonymizer1 is anonymizer2


class TestScrubText:
    def test_email_redacted(self) -> None:
        text, entity_types = pii.scrub_text(
            "Contact j.rodriguez@example.edu for details.",
            entities=pii.OUTPUT_SIDE_ENTITIES,
        )
        assert "j.rodriguez@example.edu" not in text
        assert "[EMAIL]" in text
        assert "EMAIL_ADDRESS" in entity_types

    def test_phone_redacted(self) -> None:
        text, entity_types = pii.scrub_text(
            "Call 555-123-4567 for support.",
            entities=pii.OUTPUT_SIDE_ENTITIES,
        )
        assert "555-123-4567" not in text
        assert "[PHONE]" in text
        assert "PHONE_NUMBER" in entity_types

    def test_location_redacted(self) -> None:
        text, entity_types = pii.scrub_text(
            "She works in Palo Alto full time.",
            entities=pii.OUTPUT_SIDE_ENTITIES,
        )
        assert "Palo Alto" not in text
        assert "[LOCATION]" in text
        assert "LOCATION" in entity_types

    def test_person_redacted(self) -> None:
        text, entity_types = pii.scrub_text(
            "A participant named Robert Chen disclosed personal details.",
            entities=pii.OUTPUT_SIDE_ENTITIES,
        )
        assert "Robert Chen" not in text
        assert "[PERSON]" in text
        assert "PERSON" in entity_types

    def test_person_not_redacted_when_excluded_from_entities(self) -> None:
        """Input-side-style narrow scope (no PERSON) leaves names untouched."""
        narrow = ["EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION"]
        text, entity_types = pii.scrub_text("John Smith wrote this paper.", entities=narrow)
        assert text == "John Smith wrote this paper."
        assert entity_types == []

    def test_clean_text_passes_through_unchanged(self) -> None:
        clean = "Exercise improves cognitive function across age groups."
        text, entity_types = pii.scrub_text(clean, entities=pii.OUTPUT_SIDE_ENTITIES)
        assert text == clean
        assert entity_types == []

    def test_overlapping_person_and_email_resolves_to_one_redaction(self) -> None:
        """An email string that spaCy also tags PERSON must redact once, not twice."""
        text, entity_types = pii.scrub_text(
            "Contact j.rodriguez@example.edu directly.",
            entities=pii.OUTPUT_SIDE_ENTITIES,
        )
        assert text.count("[EMAIL]") + text.count("[PERSON]") == 1
        assert "j.rodriguez@example.edu" not in text
