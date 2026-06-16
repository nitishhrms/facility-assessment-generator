"""Phase 2 tests — domain gate (pure rules + injected retrieval, offline)."""

from chat.domain import check, in_domain_rule


def test_rule_accepts_clinical_terms():
    assert in_domain_rule("What are the symptoms of sepsis?")
    assert in_domain_rule("Does metabolic syndrome affect outcomes?")


def test_rule_accepts_facility_questions():
    # In-domain via the structured/facility branch (low medical-corpus similarity).
    assert in_domain_rule("overall rating for facility 015009?")
    assert in_domain_rule("how many certified beds?")


def test_rule_defers_on_unknown():
    assert not in_domain_rule("What stock should I buy?")
    assert not in_domain_rule("Who won the game last night?")


def _fake_retrieve(top_sim):
    return lambda query, k: [{"pmid": "1", "similarity": top_sim}]


def test_rule_hit_skips_retrieval():
    def boom(query, k):
        raise AssertionError("retrieval should not run when a rule accepts")

    d = check("symptoms of diabetes", retrieve=boom)
    assert d["in_domain"] and d["stage"] == "rule"


def test_embedding_backstop_accepts_above_floor():
    d = check("some niche biomedical phrasing", retrieve=_fake_retrieve(0.88), floor=0.80)
    assert d["in_domain"] and d["stage"] == "embedding"
    assert d["top_similarity"] == 0.88


def test_embedding_backstop_refuses_below_floor():
    d = check("what stock should I buy", retrieve=_fake_retrieve(0.55), floor=0.80)
    assert not d["in_domain"]
    assert "scope" in d["answer"].lower()


def test_floor_boundary_is_inclusive():
    d = check("edge", retrieve=_fake_retrieve(0.80), floor=0.80)
    assert d["in_domain"]  # sim == floor -> in-domain


def test_empty_hits_refuses():
    d = check("totally unrelated", retrieve=lambda q, k: [], floor=0.80)
    assert not d["in_domain"]
    assert d["top_similarity"] == 0.0
