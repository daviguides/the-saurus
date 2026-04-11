from papers_mcp.schemas.results import (
    ClaimResult,
    ClaimSearchResult,
    ReviewSection,
    ThemeMapEntry,
    ThemeResult,
    ThemeReviewResult,
)


def test_theme_result():
    t = ThemeResult(paper_id="p1", name="Attention Mechanisms", description="Focus on attention")
    d = t.model_dump()
    assert d["paper_id"] == "p1"
    assert d["name"] == "Attention Mechanisms"
    assert d["positions"] == []


def test_theme_result_from_payload():
    payload = {
        "paper_id": "p1",
        "name": "Transformers",
        "description": "Architecture overview",
        "positions": [{"page": 1, "paragraph": 3, "text": "We propose..."}],
        "job_id": "j1",  # extra field from Qdrant, should be ignored
    }
    t = ThemeResult.model_validate(payload)
    assert t.name == "Transformers"
    assert len(t.positions) == 1


def test_claim_result():
    c = ClaimResult(paper_id="p1", text="Attention outperforms recurrence")
    assert c.page == 0
    assert c.theme_name == ""


def test_claim_search_result():
    claim = ClaimResult(paper_id="p1", text="Self-attention scales quadratically")
    r = ClaimSearchResult(claim=claim, score=0.95)
    d = r.model_dump()
    assert d["score"] == 0.95
    assert d["claim"]["text"] == "Self-attention scales quadratically"


def test_theme_map_entry():
    e = ThemeMapEntry(name="Efficiency", paper_ids=["p1", "p2"], aliases=["Performance"])
    assert len(e.paper_ids) == 2
    assert e.aliases == ["Performance"]


def test_theme_review_result():
    r = ThemeReviewResult(
        theme_id="t1",
        label="Efficiency",
        review="Papers agree that...",
        consensus=["Linear attention is faster"],
        gaps=["No benchmarks on long sequences"],
    )
    d = r.model_dump()
    assert d["theme_id"] == "t1"
    assert len(d["consensus"]) == 1
    assert len(d["gaps"]) == 1
    assert d["disagreements"] == []


def test_review_section():
    s = ReviewSection(theme_id="t1", title="Literature Review", label="Efficiency", content="...")
    d = s.model_dump()
    assert d["theme_id"] == "t1"
    assert d["claim_ids"] == []
