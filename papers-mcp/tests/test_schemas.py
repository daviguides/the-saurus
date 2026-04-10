from papers_mcp.schemas.results import SearchResultWithReference


def test_result_to_dict():
    r = SearchResultWithReference(
        content="Attention is all you need...",
        score=0.92,
        rank=1,
        title="Attention Is All You Need",
        authors=["Vaswani, A.", "Shazeer, N."],
        year=2017,
        doi="10.48550/arXiv.1706.03762",
        journal="NeurIPS",
    )
    d = r.to_result_dict()
    assert d["rank"] == 1
    assert "2017" in d["source"]

    ref = r.to_reference_dict()
    assert ref["doi"] == "10.48550/arXiv.1706.03762"
    assert len(ref["authors"]) == 2
