"""T1 structured answerer — parameterized SQL over the facility warehouse.

The router sends structured questions here with the CCN it extracted. We classify
the question into a small fixed set of intents and run a **parameterized** query
over `etl/warehouse.db` (the same SQLite file the vector store lives in). No
text-to-SQL: every query is a hand-written template with `?` placeholders, so there
is no injection surface and the answers are deterministic.

Each call returns a dict with a deterministic factual `answer` string plus the raw
`rows` (for the trace / citations). Intent classification is pure and unit-tests
offline; the DB connection is injectable so tests run against an in-memory warehouse.
"""

import re
import sqlite3

from chat.config import db_path

# Intents (a question maps to exactly one).
SCORECARD = "scorecard"      # overall + sub-ratings for a facility (default)
BEDS = "beds"                # certified bed count
COMPLETENESS = "completeness"  # data-quality completeness %
HISTORY = "history"          # rating trend over snapshots
RANKING = "ranking"          # rank facilities by overall rating (optional state)

_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
    "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}


def classify_intent(query: str) -> str:
    """Map a structured question to one intent. Pure."""
    q = query.lower()
    if re.search(r"\b(rank|ranking|top|highest|best|compare|leaderboard)\b", q):
        return RANKING
    if re.search(r"\b(history|trend\w*|over time|overtime)\b", q):
        return HISTORY
    # Bed count, plus common synonyms for licensed capacity.
    if re.search(r"\b(beds?|bed count|capacity|census|certified beds)\b", q):
        return BEDS
    if "completeness" in q or "data quality" in q or "complete" in q:
        return COMPLETENESS
    return SCORECARD


def _extract_state(query: str) -> str | None:
    """First valid 2-letter US state code in the query (uppercase), or None."""
    for tok in re.findall(r"\b([A-Za-z]{2})\b", query):
        if tok.upper() in _US_STATES and tok.isupper():
            return tok.upper()
    return None


def _rows(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _latest_snapshot(conn, ccn: str) -> dict | None:
    cur = conn.execute(
        """
        SELECT f.provider_name, f.state, f.certified_beds,
               s.overall_rating, s.health_rating, s.staffing_rating, s.qm_rating,
               s.completeness, s.qa_summary, s.snapshot_date, s.processing_date
        FROM   dim_facility f
        JOIN   fact_report_snapshot s ON s.ccn = f.ccn
        WHERE  f.ccn = ?
        ORDER  BY s.snapshot_date DESC
        LIMIT  1
        """,
        (ccn,),
    )
    rows = _rows(cur)
    return rows[0] if rows else None


def _answer_ranking(conn, query: str) -> dict:
    state = _extract_state(query)
    sql = """
        SELECT f.ccn, f.provider_name, f.state, s.overall_rating
        FROM   dim_facility f
        JOIN   fact_report_snapshot s ON s.ccn = f.ccn
        JOIN  (SELECT ccn, MAX(snapshot_date) AS latest
               FROM fact_report_snapshot GROUP BY ccn) m
               ON m.ccn = s.ccn AND m.latest = s.snapshot_date
        {where}
        ORDER  BY s.overall_rating DESC, f.provider_name
        LIMIT  10
    """
    if state:
        cur = conn.execute(sql.format(where="WHERE f.state = ?"), (state,))
    else:
        cur = conn.execute(sql.format(where=""))
    rows = _rows(cur)
    scope = f" in {state}" if state else ""
    if not rows:
        return {"kind": RANKING, "rows": [], "source": "warehouse",
                "answer": f"No facilities{scope} are in the warehouse yet."}
    lines = [f"{i}. {r['provider_name']} (CCN {r['ccn']}, {r['state']}) — "
             f"{_stars(r['overall_rating'])}" for i, r in enumerate(rows, 1)]
    answer = f"Facilities ranked by overall rating{scope}:\n" + "\n".join(lines)
    return {"kind": RANKING, "rows": rows, "source": "warehouse", "answer": answer}


def _stars(v) -> str:
    return f"{v}/5 stars" if v is not None else "no rating"


def answer(query: str, ccn: str | None = None, conn: sqlite3.Connection | None = None) -> dict:
    """Answer a structured question. Returns {kind, ccn, rows, answer, source}."""
    own = conn is None
    conn = conn or sqlite3.connect(db_path())
    try:
        intent = classify_intent(query)
        if intent == RANKING:
            out = _answer_ranking(conn, query)
            out["ccn"] = ccn
            return out

        if not ccn:
            return {"kind": "need_ccn", "ccn": None, "rows": [], "source": "warehouse",
                    "answer": "Which facility? Please include its 6-digit CCN "
                              "(e.g. 015009)."}

        if intent == HISTORY:
            cur = conn.execute(
                """
                SELECT snapshot_date, overall_rating, health_rating,
                       staffing_rating, qm_rating, completeness
                FROM   fact_report_snapshot
                WHERE  ccn = ?
                ORDER  BY snapshot_date
                """,
                (ccn,),
            )
            rows = _rows(cur)
            if not rows:
                return _not_found(ccn)
            if len(rows) == 1:
                r = rows[0]
                txt = (f"Only one snapshot for CCN {ccn} ({r['snapshot_date']}): "
                       f"overall {_stars(r['overall_rating'])}.")
            else:
                first, last = rows[0], rows[-1]
                txt = (f"CCN {ccn} overall rating moved from "
                       f"{_stars(first['overall_rating'])} ({first['snapshot_date']}) "
                       f"to {_stars(last['overall_rating'])} ({last['snapshot_date']}) "
                       f"across {len(rows)} snapshots.")
            return {"kind": HISTORY, "ccn": ccn, "rows": rows,
                    "source": "warehouse", "answer": txt}

        snap = _latest_snapshot(conn, ccn)
        if snap is None:
            return _not_found(ccn)

        name = snap["provider_name"]
        if intent == BEDS:
            txt = f"{name} (CCN {ccn}) has {snap['certified_beds']} certified beds."
        elif intent == COMPLETENESS:
            txt = (f"{name} (CCN {ccn}) report completeness is "
                   f"{snap['completeness']}% (as of {snap['snapshot_date']}).")
        else:  # SCORECARD
            txt = (f"{name} (CCN {ccn}, {snap['state']}) — overall "
                   f"{_stars(snap['overall_rating'])}: health "
                   f"{_stars(snap['health_rating'])}, staffing "
                   f"{_stars(snap['staffing_rating'])}, quality measures "
                   f"{_stars(snap['qm_rating'])}. Data completeness "
                   f"{snap['completeness']}%.")
        return {"kind": intent, "ccn": ccn, "rows": [snap],
                "source": "warehouse", "answer": txt}
    finally:
        if own:
            conn.close()


def _not_found(ccn: str) -> dict:
    return {"kind": "not_found", "ccn": ccn, "rows": [], "source": "warehouse",
            "answer": f"I don't have facility CCN {ccn} in the warehouse."}
