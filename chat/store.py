"""Vector store — sqlite-vec over the unified SQLite database.

Two tables:
  - chunks      : the chunk text + source metadata (PMID, section, citation URL)
  - vec_chunks  : a sqlite-vec virtual table holding the embedding per chunk,
                  keyed by the same rowid as `chunks`.

Cosine distance is used, so similarity = 1 - distance.
"""

import sqlite3

import sqlite_vec
from sqlite_vec import serialize_float32

from chat.config import EMBED_DIM, db_path


def connect(path=None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or db_path())
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks "
        f"USING vec0(embedding float[{EMBED_DIM}] distance_metric=cosine)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id             INTEGER PRIMARY KEY,
            pmid           TEXT,
            question       TEXT,
            section        TEXT,
            text           TEXT,
            long_answer    TEXT,
            source_url     TEXT,
            final_decision TEXT,
            year           TEXT
        )
        """
    )
    conn.commit()


def clear(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM vec_chunks")
    conn.execute("DELETE FROM chunks")
    conn.commit()


def count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]


def add_chunks(conn: sqlite3.Connection, chunks, vectors) -> None:
    """Insert chunk rows and their embeddings (kept in lockstep by rowid)."""
    cur = conn.cursor()
    for ch, vec in zip(chunks, vectors):
        cur.execute(
            "INSERT INTO chunks "
            "(pmid, question, section, text, long_answer, source_url, final_decision, year) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ch["pmid"], ch["question"], ch["section"], ch["text"],
             ch["long_answer"], ch["source_url"],
             ch.get("final_decision", ""), ch.get("year", "")),
        )
        cur.execute(
            "INSERT INTO vec_chunks (rowid, embedding) VALUES (?, ?)",
            (cur.lastrowid, serialize_float32([float(x) for x in vec])),
        )
    conn.commit()


def search(conn: sqlite3.Connection, query_vec, k: int = 5) -> list[dict]:
    """K-nearest chunks to `query_vec`, with cosine similarity (1 - distance)."""
    rows = conn.execute(
        """
        SELECT c.pmid, c.section, c.text, c.source_url, c.question,
               c.final_decision, c.year, v.distance
        FROM vec_chunks v
        JOIN chunks c ON c.id = v.rowid
        WHERE v.embedding MATCH ? AND k = ?
        ORDER BY v.distance
        """,
        (serialize_float32([float(x) for x in query_vec]), k),
    ).fetchall()
    return [
        {
            "pmid": r[0],
            "section": r[1],
            "text": r[2],
            "source_url": r[3],
            "question": r[4],
            "final_decision": r[5],
            "year": r[6],
            "similarity": 1.0 - r[7],
        }
        for r in rows
    ]
