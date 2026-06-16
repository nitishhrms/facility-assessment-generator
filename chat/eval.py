"""Phase 1 evaluation — retrieval quality + RAG_THRESHOLD calibration.

Two things are measured over the PubMedQA corpus (40 records -> ~128 chunks):

1. Retrieval quality (validates store + search end-to-end). For each record's
   QUESTION we run a real `store.search`; a hit is when a chunk from the record's
   OWN pmid comes back. Reported as recall@k and MRR. The own context is in the
   corpus, so this should be near-perfect; MRR catches ranking regressions.

2. RAG_THRESHOLD calibration (analytical, no physical hold-out). For each question
   we compute two max-similarities against the chunk set:
     - covered   = max sim over ALL chunks         (its own context present -> high)
     - uncovered = max sim over chunks of OTHER pmids (own context absent -> lower)
   The threshold that best separates the two distributions becomes the measured
   `RAG_THRESHOLD`, replacing the placeholder. "Best" = the value maximizing
   (covered-accept - uncovered-accept), i.e. it directly optimizes the route
   decision (answer-from-corpus vs. fall back to web search).

The pure metric functions (`recall_mrr`, `coverage_sims`, `calibrate`) take plain
arrays so they unit-test offline with fake vectors; only `evaluate()` touches the
embedding model and the store.

Example:
    python -m chat.eval --k 5
"""

import argparse
import os
import tempfile

import numpy as np

from chat import embeddings, ingest, store


def group_records(chunks: list[dict]) -> list[dict]:
    """Collapse chunks to one (pmid, question) record per source document.

    Order-preserving and pure; the first question seen for a pmid wins.
    """
    seen: dict[str, str] = {}
    for c in chunks:
        if c["pmid"] not in seen:
            seen[c["pmid"]] = c["question"]
    return [{"pmid": p, "question": q} for p, q in seen.items()]


def recall_mrr(ranked_pmids: list[list[str]], gold_pmids: list[str], k: int):
    """Recall@k and MRR given, per query, the pmids of the ranked search hits.

    `ranked_pmids[i]` is the list of pmids returned for query i, best-first (it may
    repeat a pmid when several of its chunks rank). `gold_pmids[i]` is the pmid that
    query i should retrieve. Pure.
    """
    recalls, rrs = [], []
    for ranked, gold in zip(ranked_pmids, gold_pmids):
        recalls.append(1.0 if gold in ranked[:k] else 0.0)
        rr = 0.0
        for rank, pmid in enumerate(ranked, start=1):
            if pmid == gold:
                rr = 1.0 / rank
                break
        rrs.append(rr)
    n = len(gold_pmids) or 1
    return sum(recalls) / n, sum(rrs) / n


def coverage_sims(question_vecs, chunk_vecs, chunk_owners, record_pmids):
    """Per record, the covered and uncovered max cosine similarity.

    Inputs are L2-normalized embeddings, so the cosine matrix is just the dot
    product. `chunk_owners[j]` is the pmid owning chunk j; `record_pmids[i]` is the
    pmid of query i. Returns two float arrays (covered, uncovered). Pure (numpy).
    """
    question_vecs = np.asarray(question_vecs, dtype=float)
    chunk_vecs = np.asarray(chunk_vecs, dtype=float)
    owners = np.asarray(chunk_owners)
    sims = question_vecs @ chunk_vecs.T  # (R, N) cosine
    covered, uncovered = [], []
    for i, pmid in enumerate(record_pmids):
        row = sims[i]
        covered.append(float(row.max()))
        other = row[owners != pmid]
        uncovered.append(float(other.max()) if other.size else float("-inf"))
    return np.array(covered), np.array(uncovered)


def calibrate(covered, uncovered) -> dict:
    """Pick the threshold separating covered (accept) from uncovered (fall back).

    Evaluates every candidate similarity value and maximizes
    (covered-accept-rate - uncovered-accept-rate) = Youden's J. Ties break toward the
    HIGHER threshold (more conservative: fewer uncovered queries wrongly answered from
    the corpus). Pure.
    """
    covered = np.asarray(covered, dtype=float)
    uncovered = np.asarray(uncovered, dtype=float)
    candidates = np.unique(np.concatenate([covered, uncovered]))
    best = {"threshold": float(candidates[0]), "covered_accept": 1.0,
            "uncovered_accept": 1.0, "j": 0.0}
    for t in candidates:
        ca = float(np.mean(covered >= t))
        ua = float(np.mean(uncovered >= t))
        j = ca - ua
        # >= keeps the higher threshold on ties (candidates ascend).
        if j >= best["j"]:
            best = {"threshold": float(t), "covered_accept": ca,
                    "uncovered_accept": ua, "j": j}
    return best


def evaluate(k: int = 5) -> dict:
    """Run both evaluations against a freshly built temp store. Touches the model."""
    chunks = ingest.load_chunks()
    records = group_records(chunks)

    chunk_vecs = embeddings.embed([c["text"] for c in chunks])
    question_vecs = embeddings.embed([r["question"] for r in records])
    chunk_owners = [c["pmid"] for c in chunks]
    record_pmids = [r["pmid"] for r in records]

    # 1) Retrieval quality against a real (temporary) sqlite-vec store.
    db = os.path.join(tempfile.mkdtemp(prefix="chat-eval-"), "eval.db")
    conn = store.connect(db)
    store.init_schema(conn)
    store.add_chunks(conn, chunks, chunk_vecs)
    ranked = []
    for qv in question_vecs:
        hits = store.search(conn, qv, k=max(k, 10))
        ranked.append([h["pmid"] for h in hits])
    conn.close()
    recall, mrr = recall_mrr(ranked, record_pmids, k)

    # 2) Threshold calibration (analytical covered vs. uncovered).
    covered, uncovered = coverage_sims(
        question_vecs, chunk_vecs, chunk_owners, record_pmids
    )
    cal = calibrate(covered, uncovered)

    return {
        "n_records": len(records),
        "n_chunks": len(chunks),
        "k": k,
        "recall_at_k": recall,
        "mrr": mrr,
        "covered_mean": float(np.mean(covered)),
        "uncovered_mean": float(np.mean(uncovered)),
        "calibration": cal,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Phase 1 retrieval eval + threshold calibration.")
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args(argv)

    r = evaluate(k=args.k)
    cal = r["calibration"]
    print(f"Corpus: {r['n_records']} records, {r['n_chunks']} chunks\n")
    print(f"Retrieval quality (own-pmid as gold):")
    print(f"  recall@{r['k']} = {r['recall_at_k']:.3f}")
    print(f"  MRR        = {r['mrr']:.3f}\n")
    print(f"Similarity distributions (max cosine per query):")
    print(f"  covered   mean = {r['covered_mean']:.3f}  (own context in corpus)")
    print(f"  uncovered mean = {r['uncovered_mean']:.3f}  (own context excluded)\n")
    print(f"Recommended RAG_THRESHOLD = {cal['threshold']:.3f}")
    print(f"  at this cut: covered-accept = {cal['covered_accept']:.2f}, "
          f"uncovered-accept = {cal['uncovered_accept']:.2f}, J = {cal['j']:.2f}")
    print(f"\n  export RAG_THRESHOLD={cal['threshold']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
