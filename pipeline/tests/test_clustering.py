"""Tests for divide-and-conquer theme clustering: coarse-cluster + reconcile."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from pipeline.core.clustering import (
    MAX_BUCKET_SIZE,
    _cap_bucket_sizes,
    _cosine,
    cluster_themes,
    reconcile_canonical_themes,
)

# --- _cosine ---


def test_cosine_identical_vectors_is_one() -> None:
    assert _cosine([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_cosine_orthogonal_vectors_is_zero() -> None:
    assert _cosine([1.0, 0.0], [0.0, 1.0]) == 0.0


# --- cluster_themes ---


def _theme(name: str, desc: str) -> dict:
    return {"name": name, "description": desc}


async def test_cluster_themes_short_circuits_on_zero_or_one() -> None:
    with patch("pipeline.core.clustering.embed_batch", new_callable=AsyncMock) as mock_embed:
        assert await cluster_themes([]) == []
        assert await cluster_themes([_theme("A", "a")]) == [[0]]
        mock_embed.assert_not_called()


async def test_cluster_themes_groups_similar_vectors() -> None:
    themes = [_theme("Chronobiology", "x"), _theme("Circadian Biology", "y")]

    with (
        patch(
            "pipeline.core.clustering.embed_batch",
            new_callable=AsyncMock,
            return_value=[[1.0, 0.0], [0.99, 0.01]],
        ),
        patch("pipeline.core.clustering.extract_entities", return_value=set()),
    ):
        buckets = await cluster_themes(themes)

    assert buckets == [[0, 1]]


async def test_cluster_themes_separates_dissimilar_vectors() -> None:
    themes = [_theme("Chronobiology", "x"), _theme("Gene Therapy", "y")]

    with (
        patch(
            "pipeline.core.clustering.embed_batch",
            new_callable=AsyncMock,
            return_value=[[1.0, 0.0], [0.0, 1.0]],
        ),
        patch("pipeline.core.clustering.extract_entities", return_value=set()),
    ):
        buckets = await cluster_themes(themes)

    assert sorted(buckets) == [[0], [1]]


async def test_cluster_themes_entity_overlap_boosts_borderline_pair() -> None:
    # cosine ~0.75: below COARSE_COSINE_THRESHOLD (0.80), above the
    # entity-boosted threshold (0.72) — merges only because entities overlap.
    themes = [_theme("Chronobiology", "boston study"), _theme("Circadian Rhythms", "boston trial")]
    vectors = [[1.0, 0.0], [0.75, 0.6614]]  # cosine ≈ 0.75

    with (
        patch(
            "pipeline.core.clustering.embed_batch",
            new_callable=AsyncMock,
            return_value=vectors,
        ),
        patch(
            "pipeline.core.clustering.extract_entities",
            side_effect=[{"boston"}, {"boston"}],
        ),
    ):
        boosted_buckets = await cluster_themes(themes)

    with (
        patch(
            "pipeline.core.clustering.embed_batch",
            new_callable=AsyncMock,
            return_value=vectors,
        ),
        patch(
            "pipeline.core.clustering.extract_entities",
            side_effect=[set(), set()],
        ),
    ):
        unboosted_buckets = await cluster_themes(themes)

    assert boosted_buckets == [[0, 1]]
    assert sorted(unboosted_buckets) == [[0], [1]]


# --- _cap_bucket_sizes ---


def test_cap_bucket_sizes_splits_oversized_bucket() -> None:
    n = 2 * MAX_BUCKET_SIZE + 1
    bucket = list(range(n))
    vectors = [[float(i + 1), 0.0] for i in range(n)]

    result = _cap_bucket_sizes([bucket], vectors)

    assert len(result) == 3
    assert all(len(sub) <= MAX_BUCKET_SIZE for sub in result)
    assert sorted(i for sub in result for i in sub) == bucket


def test_cap_bucket_sizes_leaves_small_bucket_untouched() -> None:
    bucket = [0, 1, 2]
    vectors = [[1.0, 0.0], [0.9, 0.1], [0.8, 0.2]]

    result = _cap_bucket_sizes([bucket], vectors)

    assert result == [bucket]


# --- reconcile_canonical_themes ---


def _canonical(theme_id: str, name: str) -> dict:
    return {
        "id": theme_id,
        "name": name,
        "label": name,
        "description": "desc",
        "paper_ids": [f"p-{theme_id}"],
        "aliases": [name],
        "source_theme_ids": [f"src-{theme_id}"],
    }


async def test_reconcile_short_circuits_on_zero_or_one() -> None:
    with patch("pipeline.core.clustering.embed_batch", new_callable=AsyncMock) as mock_embed:
        themes, tmap = await reconcile_canonical_themes([], {})
        assert themes == []
        assert tmap == {}

        single = [_canonical("c1", "Chronobiology")]
        themes, tmap = await reconcile_canonical_themes(single, {"c1": ["t1"]})
        assert themes == single
        assert tmap == {"c1": ["t1"]}

        mock_embed.assert_not_called()


async def test_reconcile_merges_similar_canonical_themes() -> None:
    canonical = [_canonical("c1", "Chronobiology"), _canonical("c2", "Circadian Biology")]
    theme_map = {"c1": ["t1"], "c2": ["t3"]}

    with patch(
        "pipeline.core.clustering.embed_batch",
        new_callable=AsyncMock,
        return_value=[[1.0, 0.0], [0.99, 0.01]],
    ):
        merged_themes, merged_map = await reconcile_canonical_themes(canonical, theme_map)

    assert len(merged_themes) == 1
    merged = merged_themes[0]
    assert set(merged["paper_ids"]) == {"p-c1", "p-c2"}
    assert set(merged["aliases"]) == {"Chronobiology", "Circadian Biology"}
    assert set(merged["source_theme_ids"]) == {"src-c1", "src-c2"}
    assert set(merged_map[merged["id"]]) == {"t1", "t3"}


async def test_reconcile_leaves_dissimilar_themes_unmerged() -> None:
    canonical = [_canonical("c1", "Chronobiology"), _canonical("c2", "Gene Therapy")]
    theme_map = {"c1": ["t1"], "c2": ["t2"]}

    with patch(
        "pipeline.core.clustering.embed_batch",
        new_callable=AsyncMock,
        return_value=[[1.0, 0.0], [0.0, 1.0]],
    ):
        merged_themes, merged_map = await reconcile_canonical_themes(canonical, theme_map)

    assert len(merged_themes) == 2
    assert merged_map == theme_map
