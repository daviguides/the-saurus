"""Reusable spaCy entity extractor: standalone, no ingestion pipeline dependency."""

from __future__ import annotations

import spacy

MODEL_NAME = "en_core_web_sm"

_nlp = spacy.load(MODEL_NAME)


def extract_entities(text: str) -> set[str]:
    """Extract normalized (lowercased, stripped) named-entity text spans from text."""
    doc = _nlp(text)
    return {ent.text.lower().strip() for ent in doc.ents}
