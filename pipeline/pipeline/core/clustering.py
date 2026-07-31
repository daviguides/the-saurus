"""Divide-and-conquer theme clustering: coarse-cluster (map) + reconcile (reduce).

Coarse-cluster uses embedding cosine similarity as the primary signal and spaCy
named-entity overlap as a threshold-lowering boost (never a gate — theme descriptions
are abstract scientific concepts, not named entities, so entity overlap is sparse).
Reconcile merges bucket-canonical themes by embedding similarity alone (no second LLM
call), which keeps the "any single LLM call bounded to largest bucket" guarantee
unconditional regardless of how much duplication the per-bucket LLM calls found.
"""

from __future__ import annotations

from math import ceil
from typing import Any
from uuid import uuid4

import numpy as np

from .embedding import embed_batch
from .entities import extract_entities

COARSE_COSINE_THRESHOLD = 0.80
COARSE_COSINE_THRESHOLD_WITH_ENTITY_OVERLAP = 0.72
MAX_BUCKET_SIZE = 20
RECONCILE_COSINE_THRESHOLD = 0.85


def _cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a), np.asarray(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))


class _UnionFind:
    def __init__(self, n: int) -> None:
        self._parent = list(range(n))

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb

    def groups(self) -> list[list[int]]:
        out: dict[int, list[int]] = {}
        for i in range(len(self._parent)):
            out.setdefault(self.find(i), []).append(i)
        return list(out.values())


async def cluster_themes(themes: list[dict[str, Any]]) -> list[list[int]]:
    """Coarse-cluster theme indices via embedding cosine + NER overlap boost.

    Returns buckets of theme indices (into `themes`), each capped at
    MAX_BUCKET_SIZE.
    """
    if len(themes) <= 1:
        return [[i] for i in range(len(themes))]

    texts = [f"{t.get('name', '')}: {t.get('description', '')}" for t in themes]
    vectors = await embed_batch(texts)
    entity_sets = [extract_entities(t.get("description", "")) for t in themes]

    uf = _UnionFind(len(themes))
    for i in range(len(themes)):
        for j in range(i + 1, len(themes)):
            threshold = (
                COARSE_COSINE_THRESHOLD_WITH_ENTITY_OVERLAP
                if entity_sets[i] & entity_sets[j]
                else COARSE_COSINE_THRESHOLD
            )
            if _cosine(vectors[i], vectors[j]) >= threshold:
                uf.union(i, j)

    return _cap_bucket_sizes(uf.groups(), vectors)


def _cap_bucket_sizes(
    buckets: list[list[int]], vectors: list[list[float]],
) -> list[list[int]]:
    """Split any bucket over MAX_BUCKET_SIZE by descending distance from centroid."""
    result: list[list[int]] = []
    for bucket in buckets:
        if len(bucket) <= MAX_BUCKET_SIZE:
            result.append(bucket)
            continue
        n_sub = ceil(len(bucket) / MAX_BUCKET_SIZE)
        centroid = np.mean([vectors[i] for i in bucket], axis=0).tolist()
        ordered = sorted(bucket, key=lambda i: -_cosine(vectors[i], centroid))
        subs: list[list[int]] = [[] for _ in range(n_sub)]
        for pos, theme_idx in enumerate(ordered):
            subs[pos % n_sub].append(theme_idx)
        result.extend(subs)
    return result


async def reconcile_canonical_themes(
    canonical_themes: list[dict[str, Any]],
    theme_map: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Merge cross-bucket duplicate canonical themes via embedding similarity (reduce phase)."""
    if len(canonical_themes) <= 1:
        return canonical_themes, theme_map

    texts = [f"{t['name']}: {t.get('description', '')}" for t in canonical_themes]
    vectors = await embed_batch(texts)

    uf = _UnionFind(len(canonical_themes))
    for i in range(len(canonical_themes)):
        for j in range(i + 1, len(canonical_themes)):
            if _cosine(vectors[i], vectors[j]) >= RECONCILE_COSINE_THRESHOLD:
                uf.union(i, j)

    merged_themes: list[dict[str, Any]] = []
    merged_map: dict[str, list[str]] = {}
    for indices in uf.groups():
        primary = canonical_themes[indices[0]]
        canonical_id = primary["id"] if len(indices) == 1 else str(uuid4())

        paper_ids: list[str] = []
        aliases: list[str] = []
        source_ids: list[str] = []
        for idx in indices:
            t = canonical_themes[idx]
            for pid in t.get("paper_ids", []):
                if pid not in paper_ids:
                    paper_ids.append(pid)
            for alias in t.get("aliases", []):
                if alias not in aliases:
                    aliases.append(alias)
            source_ids.extend(t.get("source_theme_ids", []))
            merged_map.setdefault(canonical_id, []).extend(
                theme_map.get(t["id"], [])
            )

        merged_themes.append({
            "id": canonical_id,
            "name": primary["name"],
            "label": primary["name"],
            "description": primary["description"],
            "paper_ids": paper_ids,
            "aliases": aliases,
            "source_theme_ids": source_ids,
        })

    return merged_themes, merged_map
