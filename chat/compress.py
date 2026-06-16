"""Extractive context compression — the "shorten" stage (brief line 6).

Before Claude answers a T2 (RAG) question, trim the retrieved chunks to the sentences
that actually bear on the query. This is pure, deterministic, and free (no model, no
API): split each chunk into sentences, rank them by lexical overlap with the query,
keep the top-N, then restore natural reading order. Each kept sentence keeps its source
attribution (pmid / url / section) so `generate.py` can cite it.

It is deliberately a *lightweight* pass — with Claude's context window the token saving
is modest; the value is dropping obvious noise and honoring the brief's two-stage
("shorten, then answer") design. The sentence `scorer` is injectable, so an embedding
scorer could replace the lexical default without touching the ranking logic.
"""

import re

from chat.config import COMPRESS_MAX_SENTENCES

# Tiny stopword set — enough to stop function words from dominating the overlap score.
_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
    "was", "were", "be", "been", "by", "with", "as", "at", "that", "this", "it",
    "from", "do", "does", "did", "how", "what", "which", "who", "whom", "why",
    "when", "we", "i", "you", "they", "their", "its", "has", "have", "had",
}

# Split on sentence-ending punctuation followed by whitespace + a capital/digit. The
# lookbehind/lookahead avoid splitting decimals ("0.5 mg") and lower-case abbreviations.
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_WORD = re.compile(r"[a-z0-9]+")
_MIN_SENTENCE_CHARS = 15


def split_sentences(text: str) -> list[str]:
    """Split text into trimmed, non-trivial sentences. Pure."""
    if not text:
        return []
    return [s.strip() for s in _SENT_SPLIT.split(text.strip()) if s.strip()]


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _STOPWORDS}


def lexical_scorer(query: str):
    """Return a scorer(sentence) -> fraction of query content-words it contains. Pure."""
    q = _tokens(query)

    def score(sentence: str) -> float:
        if not q:
            return 0.0
        return len(q & _tokens(sentence)) / len(q)

    return score


def shorten(query, hits, max_sentences: int = COMPRESS_MAX_SENTENCES, scorer=None) -> list[dict]:
    """Keep the `max_sentences` most query-relevant sentences across `hits`.

    Returns sentence dicts (text + source attribution + score) in natural reading
    order. Ranking: lexical score desc, then the source chunk's retrieval similarity
    desc, then original position (stable). `scorer(sentence) -> float` is injectable.
    """
    scorer = scorer or lexical_scorer(query)
    candidates = []
    for hi, h in enumerate(hits or []):
        for si, sent in enumerate(split_sentences(h.get("text", ""))):
            if len(sent) < _MIN_SENTENCE_CHARS:
                continue
            candidates.append({
                "text": sent,
                "pmid": h.get("pmid"),
                "source_url": h.get("source_url"),
                "section": h.get("section"),
                "hit_index": hi,
                "sent_index": si,
                "chunk_similarity": h.get("similarity", 0.0),
                "score": scorer(sent),
            })
    if not candidates:
        return []

    ranked = sorted(
        candidates,
        key=lambda c: (-c["score"], -c["chunk_similarity"], c["hit_index"], c["sent_index"]),
    )
    kept = ranked[:max_sentences]
    kept.sort(key=lambda c: (c["hit_index"], c["sent_index"]))  # restore reading order
    return kept
