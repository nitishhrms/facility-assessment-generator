"""Ingestion CLI — PubMedQA corpus -> chunks -> embeddings -> sqlite-vec.

Each PubMedQA record contributes one chunk per CONTEXT paragraph, carrying its
section label and a PubMed citation URL built from the PMID.

Examples:
    python -m chat.ingest
    python -m chat.ingest --query "does metabolic syndrome affect outcomes?"
"""

import argparse
import json

from chat import embeddings, store
from chat.config import EMBED_DIM, EMBED_MODEL, SAMPLE_PATH


def record_to_chunks(pmid: str, rec: dict) -> list[dict]:
    """Turn one PubMedQA record into per-paragraph chunks (pure function)."""
    contexts = rec.get("CONTEXTS") or []
    labels = rec.get("LABELS") or []
    question = rec.get("QUESTION") or ""
    long_answer = rec.get("LONG_ANSWER") or ""
    final_decision = rec.get("final_decision") or ""
    year = str(rec.get("YEAR") or "")
    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    chunks = []
    for i, ctx in enumerate(contexts):
        if not ctx or not ctx.strip():
            continue
        chunks.append(
            {
                "pmid": pmid,
                "question": question,
                "section": labels[i] if i < len(labels) else "",
                "text": ctx.strip(),
                "long_answer": long_answer,
                "source_url": url,
                "final_decision": final_decision,
                "year": year,
            }
        )
    return chunks


def load_chunks(path=SAMPLE_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    chunks = []
    for pmid, rec in data.items():
        chunks.extend(record_to_chunks(pmid, rec))
    return chunks


def ingest(path=SAMPLE_PATH, reset: bool = True) -> int:
    conn = store.connect()
    store.init_schema(conn)
    if reset:
        store.clear(conn)
    chunks = load_chunks(path)
    vectors = embeddings.embed([c["text"] for c in chunks])
    if vectors.shape[1] != EMBED_DIM:
        raise ValueError(
            f"Embedding dim {vectors.shape[1]} != EMBED_DIM {EMBED_DIM}; "
            f"the vec_chunks table is fixed at float[{EMBED_DIM}]. "
            f"Set EMBED_DIM to match {EMBED_MODEL} or rebuild the store."
        )
    store.add_chunks(conn, chunks, vectors)
    total = store.count(conn)
    print(f"Ingested {len(chunks)} chunks from {path} (store now holds {total}).")
    return len(chunks)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Ingest PubMedQA into the vector store.")
    ap.add_argument("--path", default=str(SAMPLE_PATH))
    ap.add_argument("--query", help="Run a similarity query after ingestion.")
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args(argv)

    ingest(args.path)

    if args.query:
        conn = store.connect()
        qv = embeddings.embed([args.query])[0]
        print(f"\nTop {args.k} for: {args.query!r}")
        for r in store.search(conn, qv, k=args.k):
            print(f"  sim={r['similarity']:.3f}  [{r['section']}] PMID {r['pmid']}: "
                  f"{r['text'][:100]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
