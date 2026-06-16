"""Phase 2 tests — intent router (pure detection + injected retrieval, offline)."""

from chat.router import (
    T1_STRUCTURED,
    T2_RAG,
    T3_WEB,
    extract_ccn,
    looks_structured,
    route,
)


def test_extract_ccn():
    assert extract_ccn("overall rating for CCN 015009?") == "015009"
    assert extract_ccn("facility 12345 and 678901") == "678901"  # first 6-digit wins
    assert extract_ccn("no number here") is None
    assert extract_ccn("12345 is only five digits") is None


def test_looks_structured_metrics_and_ccn():
    assert looks_structured("What is the staffing rating for 015009?")
    assert looks_structured("How many certified beds does it have?")
    assert looks_structured("show me the overall rating")
    # Clinical-literature questions must NOT look structured.
    assert not looks_structured("Do mitochondria affect programmed cell death?")
    assert not looks_structured("natural history of untreated hypertension")  # no CCN


def test_route_t1_structured_short_circuits_retrieval():
    def boom(query, k):  # retrieval must not be called for T1
        raise AssertionError("retrieve should not run for structured queries")

    d = route("overall rating for 015009?", retrieve=boom)
    assert d["tier"] == T1_STRUCTURED
    assert d["source"] == "structured"
    assert d["ccn"] == "015009"


def _fake_retrieve(top_sim):
    return lambda query, k: [{"pmid": "1", "text": "ctx", "similarity": top_sim}]


def test_route_t2_rag_when_similarity_clears_threshold():
    d = route("does metabolic syndrome affect outcomes?",
              retrieve=_fake_retrieve(0.95), threshold=0.916)
    assert d["tier"] == T2_RAG
    assert d["source"] == "rag"
    assert d["top_similarity"] == 0.95
    assert d["hits"][0]["pmid"] == "1"


def test_route_t3_web_when_below_threshold():
    d = route("latest 2025 sepsis guidelines?",
              retrieve=_fake_retrieve(0.40), threshold=0.916)
    assert d["tier"] == T3_WEB
    assert d["source"] == "web"
    assert d["top_similarity"] == 0.40


def test_route_threshold_boundary_is_inclusive():
    d = route("edge case", retrieve=_fake_retrieve(0.916), threshold=0.916)
    assert d["tier"] == T2_RAG  # sim == threshold -> RAG


def test_route_empty_hits_falls_to_web():
    d = route("uncovered query", retrieve=lambda q, k: [], threshold=0.916)
    assert d["tier"] == T3_WEB
    assert d["top_similarity"] == 0.0
