"""Phase 3 tests — extractive compression (pure, offline)."""

from chat.compress import lexical_scorer, shorten, split_sentences


def test_split_sentences_basic():
    s = split_sentences("Sepsis is severe. It causes organ failure! Is it treatable?")
    assert s == ["Sepsis is severe.", "It causes organ failure!", "Is it treatable?"]


def test_split_sentences_keeps_decimals_and_abbreviations():
    # "0.5 mg" must not split; lower-case "e.g." must not split.
    s = split_sentences("Give 0.5 mg daily, e.g. at night. Monitor the patient closely.")
    assert s == ["Give 0.5 mg daily, e.g. at night.", "Monitor the patient closely."]


def test_lexical_scorer_overlap_fraction():
    score = lexical_scorer("mitochondria programmed cell death")
    # 4 content words; sentence covers 3 of them -> 0.75.
    assert score("Mitochondria drive programmed death in cells") == 0.75
    assert score("completely unrelated banking sentence") == 0.0


def test_shorten_ranks_and_caps():
    hits = [{
        "pmid": "1", "source_url": "u1", "section": "RESULTS", "similarity": 0.9,
        "text": ("Mitochondria play a key role in programmed cell death. "
                 "The weather was pleasant that week. "
                 "Cell death was observed in the tissue."),
    }]
    out = shorten("programmed cell death mitochondria", hits, max_sentences=2)
    assert len(out) == 2
    texts = " ".join(c["text"] for c in out)
    assert "weather" not in texts                       # off-topic sentence dropped
    assert "Mitochondria play a key role" in texts


def test_shorten_preserves_reading_order_after_selection():
    hits = [{
        "pmid": "1", "source_url": "u1", "similarity": 0.9,
        "text": "Alpha relevant cell. Beta filler text here. Gamma relevant death.",
    }]
    out = shorten("relevant", hits, max_sentences=2)
    # Both 'relevant' sentences kept; order must follow the source, not the score.
    assert [c["sent_index"] for c in out] == sorted(c["sent_index"] for c in out)
    assert out[0]["text"].startswith("Alpha")


def test_shorten_carries_attribution():
    hits = [{"pmid": "42", "source_url": "url42", "section": "BACKGROUND",
             "similarity": 0.8, "text": "Relevant clinical finding about sepsis here."}]
    out = shorten("sepsis finding", hits, max_sentences=1)
    assert out[0]["pmid"] == "42"
    assert out[0]["source_url"] == "url42"
    assert out[0]["section"] == "BACKGROUND"


def test_shorten_tie_breaks_by_chunk_similarity():
    # Same lexical score (both contain "sepsis"); higher-similarity chunk wins the slot.
    hits = [
        {"pmid": "low", "source_url": "u", "similarity": 0.5, "text": "Sepsis case one here."},
        {"pmid": "high", "source_url": "u", "similarity": 0.95, "text": "Sepsis case two here."},
    ]
    out = shorten("sepsis", hits, max_sentences=1)
    assert out[0]["pmid"] == "high"


def test_shorten_empty_hits():
    assert shorten("anything", []) == []
    assert shorten("anything", None) == []
