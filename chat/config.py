"""Chat-system configuration (env-overridable).

The vector store lives in the SAME SQLite file as the warehouse (unified store),
so structured (SQL) and unstructured (RAG) answers share one database.
"""

import os
from pathlib import Path

CHAT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CHAT_DIR.parent
DATA_DIR = CHAT_DIR / "data"
SAMPLE_PATH = DATA_DIR / "pubmedqa_sample.json"

# Biomedical sentence-embedding model (PubMedBERT family, tuned for retrieval).
EMBED_MODEL = os.environ.get("EMBED_MODEL", "pritamdeka/S-PubMedBert-MS-MARCO")
EMBED_DIM = int(os.environ.get("EMBED_DIM", "768"))

# Below this top cosine similarity, RAG hands off to web search (Phase 3).
# Calibrated via `python -m chat.eval` (maximizes covered-accept - uncovered-accept):
# covered-accept 0.90 / uncovered-accept 0.03 / J 0.88. PubMedBERT clusters biomedical
# text in a high-similarity band, so this floor sits far above a naive 0.5.
RAG_THRESHOLD = float(os.environ.get("RAG_THRESHOLD", "0.916"))

# Out-of-domain floor for the domain gate's embedding backstop (chat.domain). A query
# with no healthcare/facility keyword AND a max corpus similarity below this is treated
# as out-of-domain and politely refused.
# Calibrated via `python -m chat.domain --probe`: in-domain probes scored 0.89-0.94,
# off-domain (stocks/sports/poetry) 0.84-0.86 — PubMedBERT packs all text into a high
# band, so the separating gap is thin (~0.861-0.892). 0.88 sits in that gap. The margin
# is small by design: the RULE stage is the reliable domain signal; this is a backstop.
DOMAIN_FLOOR = float(os.environ.get("DOMAIN_FLOOR", "0.88"))

# Block threshold for the security gate's embedding backstop (chat.security): a query
# whose max similarity to the unsafe exemplars meets this is blocked. The regex rules
# are primary; this catches paraphrases they miss.
# Calibrated via `python -m chat.security --probe`: safe queries scored 0.83-0.885,
# unsafe paraphrases 0.911-0.916 — a clean gap at (0.885, 0.911]. 0.90 sits in it with
# ~0.015 buffer each side (better separation than the domain gate).
SECURITY_THRESHOLD = float(os.environ.get("SECURITY_THRESHOLD", "0.90"))

# Max sentences the extractive compressor (chat.compress) keeps before generation.
COMPRESS_MAX_SENTENCES = int(os.environ.get("COMPRESS_MAX_SENTENCES", "6"))


def db_path() -> str:
    """Unified SQLite DB path (shared with the ETL warehouse)."""
    return os.environ.get("CHAT_DB") or str(PROJECT_ROOT / "etl" / "warehouse.db")
