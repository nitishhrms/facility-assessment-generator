"""Phase 1 tests — chunking (pure) + vector store search.

These use fake vectors, so they exercise sqlite-vec without downloading the
embedding model (fast, offline).
"""

import os
import tempfile

from chat import store
from chat.config import EMBED_DIM
from chat.ingest import record_to_chunks


def test_record_to_chunks():
    rec = {
        "QUESTION": "Does X cause Y?",
        "CONTEXTS": ["background text", "results text", ""],  # blank dropped
        "LABELS": ["BACKGROUND", "RESULTS"],
        "LONG_ANSWER": "Yes, in this cohort.",
    }
    chunks = record_to_chunks("12345", rec)
    assert len(chunks) == 2
    assert chunks[0]["pmid"] == "12345"
    assert chunks[0]["section"] == "BACKGROUND"
    assert chunks[1]["section"] == "RESULTS"
    assert chunks[0]["source_url"] == "https://pubmed.ncbi.nlm.nih.gov/12345/"
    assert chunks[0]["question"] == "Does X cause Y?"


def _one_hot(i: int):
    v = [0.0] * EMBED_DIM
    v[i] = 1.0
    return v


def test_store_add_and_search():
    db = os.path.join(tempfile.mkdtemp(), "vec.db")
    conn = store.connect(db)
    store.init_schema(conn)

    chunks = [
        {"pmid": "1", "question": "", "section": "A", "text": "alpha",
         "long_answer": "", "source_url": "u1"},
        {"pmid": "2", "question": "", "section": "B", "text": "beta",
         "long_answer": "", "source_url": "u2"},
        {"pmid": "3", "question": "", "section": "C", "text": "gamma",
         "long_answer": "", "source_url": "u3"},
    ]
    vectors = [_one_hot(0), _one_hot(1), _one_hot(2)]
    store.add_chunks(conn, chunks, vectors)

    assert store.count(conn) == 3

    # Query closest to the second chunk's vector.
    results = store.search(conn, _one_hot(1), k=3)
    assert results[0]["pmid"] == "2"               # nearest neighbor
    assert abs(results[0]["similarity"] - 1.0) < 1e-5  # identical vector -> sim ~1
    assert results[0]["similarity"] >= results[1]["similarity"]  # sorted desc
