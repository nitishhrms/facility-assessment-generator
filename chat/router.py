"""Intent router — tiered T1 (structured/SQL) -> T2 (RAG) -> T3 (web search).

Matches the ordering in the brief: try a cheap deterministic rule first, then the
embedding corpus, then the web as a last resort.

  - T1 STRUCTURED : the query names a facility (6-digit CCN) or a warehouse metric
                    (rating / beds / staffing / completeness ...). Answered by SQL
                    over `etl/warehouse.db` (see `sql_answer.py`). Deterministic.
  - T2 RAG        : embedding retrieval finds corpus chunks whose top cosine
                    similarity clears `RAG_THRESHOLD` (calibrated in Phase 1).
  - T3 WEB        : in-domain but the corpus does not cover it (top sim below the
                    floor) -> hand off to Claude's web_search (Phase 3).

Rule detection (`extract_ccn`, `looks_structured`) is pure and unit-tests offline.
The embedding step is reached through an injectable `retrieve` seam so routing logic
can be tested without loading the model. The router only *decides*; the gates
(`security.py`, `domain.py`) run before it and answer generation runs after it.
"""

import re

from chat.config import RAG_THRESHOLD

T1_STRUCTURED = "T1"
T2_RAG = "T2"
T3_WEB = "T3"

# A CMS Certification Number: six digits (e.g. "015009").
CCN_RE = re.compile(r"\b(\d{6})\b")

# Facility-specific warehouse metrics. Kept narrow on purpose so clinical-literature
# questions don't get pulled into the SQL tier; ambiguous words like "history" only
# count as structured when a CCN is also present (handled in `looks_structured`).
_METRIC_KEYWORDS = [
    r"ratings?", r"rated", r"rank\w*", r"star ratings?", r"beds?",
    r"certified beds", r"completeness", r"staffing", r"quality measures?",
    r"qm", r"health inspection", r"overall rating",
]
_METRIC_RE = re.compile(r"\b(" + "|".join(_METRIC_KEYWORDS) + r")\b", re.IGNORECASE)

# Facility-history terms: only meaningful as structured when tied to a CCN.
_HISTORY_RE = re.compile(r"\b(history|trend\w*|snapshot|over time)\b", re.IGNORECASE)


def extract_ccn(query: str) -> str | None:
    """First 6-digit CCN in the query, or None. Pure."""
    m = CCN_RE.search(query)
    return m.group(1) if m else None


def looks_structured(query: str) -> bool:
    """True when the query targets the facility warehouse rather than literature. Pure."""
    if extract_ccn(query):
        return True
    if _METRIC_RE.search(query):
        return True
    # "history"/"trend" alone is usually clinical; only structured with a CCN (above).
    return False


def default_retrieve(query: str, k: int = 5) -> list[dict]:
    """Real embedding retrieval over the vector store (lazy, model-backed)."""
    from chat import embeddings, store  # heavy imports kept out of module import

    conn = store.connect()
    qv = embeddings.embed([query])[0]
    return store.search(conn, qv, k=k)


def route(query, retrieve=None, k: int = 5, threshold: float = RAG_THRESHOLD) -> dict:
    """Decide the tier for `query` and carry the evidence the answer stage needs.

    `retrieve(query, k) -> list[hit dict]` is injectable so routing unit-tests run
    offline; in production it defaults to embedding + vector search.
    """
    if looks_structured(query):
        return {
            "tier": T1_STRUCTURED,
            "source": "structured",
            "query": query,
            "ccn": extract_ccn(query),
        }

    retrieve = retrieve or default_retrieve
    hits = retrieve(query, k)
    top = hits[0]["similarity"] if hits else 0.0
    tier = T2_RAG if top >= threshold else T3_WEB
    return {
        "tier": tier,
        "source": "rag" if tier == T2_RAG else "web",
        "query": query,
        "hits": hits,
        "top_similarity": top,
    }
