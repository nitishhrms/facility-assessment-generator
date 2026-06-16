"""Phase 2 tests — structured answerer over an in-memory warehouse (offline)."""

import sqlite3
from pathlib import Path

import pytest

from chat import sql_answer
from chat.sql_answer import (
    BEDS,
    COMPLETENESS,
    HISTORY,
    RANKING,
    SCORECARD,
    classify_intent,
)

SCHEMA = Path(__file__).resolve().parents[2] / "etl" / "schema.sql"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA.read_text(encoding="utf-8"))
    c.executescript(
        """
        INSERT INTO dim_facility (ccn, provider_name, state, certified_beds, updated_at)
        VALUES ('015009', 'BURNS NURSING HOME, INC.', 'AL', 57, '2026-06-18'),
               ('686123', 'KENDALL LAKES HEALTHCARE', 'FL', 150, '2026-06-18');

        INSERT INTO fact_report_snapshot
          (id, ccn, snapshot_date, overall_rating, health_rating, staffing_rating,
           qm_rating, completeness, processing_date, created_at)
        VALUES
          ('a', '015009', '2026-05-01', 1, 1, 3, 4, 90, '2026-05-01', '2026-05-01'),
          ('b', '015009', '2026-06-18', 2, 2, 4, 4, 100, '2026-06-18', '2026-06-18'),
          ('c', '686123', '2026-06-18', 5, 5, 2, 5, 100, '2026-06-18', '2026-06-18');
        """
    )
    yield c
    c.close()


def test_classify_intent():
    assert classify_intent("what is the overall rating for 015009?") == SCORECARD
    assert classify_intent("how many certified beds?") == BEDS
    assert classify_intent("what is census capacity for 686123?") == BEDS  # synonyms
    assert classify_intent("what's the bed capacity?") == BEDS
    assert classify_intent("what's the data completeness?") == COMPLETENESS
    assert classify_intent("show the rating history for 015009") == HISTORY
    assert classify_intent("rank the top facilities in FL") == RANKING
    assert classify_intent("staffing rating for 015009") == SCORECARD  # sub-rating -> scorecard


def test_scorecard(conn):
    out = sql_answer.answer("overall rating for 015009?", ccn="015009", conn=conn)
    assert out["kind"] == SCORECARD
    assert out["rows"][0]["overall_rating"] == 2          # latest snapshot, not the older 1
    assert "BURNS NURSING HOME" in out["answer"]
    assert "2/5 stars" in out["answer"]
    assert "staffing 4/5" in out["answer"]


def test_beds(conn):
    out = sql_answer.answer("how many certified beds does 686123 have?", ccn="686123", conn=conn)
    assert out["kind"] == BEDS
    assert "150 certified beds" in out["answer"]


def test_completeness(conn):
    out = sql_answer.answer("data completeness for 015009", ccn="015009", conn=conn)
    assert out["kind"] == COMPLETENESS
    assert "100%" in out["answer"]


def test_history_multiple_snapshots(conn):
    out = sql_answer.answer("rating history for 015009", ccn="015009", conn=conn)
    assert out["kind"] == HISTORY
    assert len(out["rows"]) == 2
    assert "1/5 stars" in out["answer"] and "2/5 stars" in out["answer"]  # trend endpoints


def test_ranking_with_state_filter(conn):
    out = sql_answer.answer("rank top facilities in FL", conn=conn)
    assert out["kind"] == RANKING
    assert len(out["rows"]) == 1
    assert out["rows"][0]["ccn"] == "686123"


def test_ranking_all_states_orders_by_rating(conn):
    out = sql_answer.answer("rank facilities by overall rating", conn=conn)
    assert [r["ccn"] for r in out["rows"]] == ["686123", "015009"]  # 5 stars before 2


def test_not_found(conn):
    out = sql_answer.answer("rating for 999999", ccn="999999", conn=conn)
    assert out["kind"] == "not_found"


def test_need_ccn_when_missing(conn):
    out = sql_answer.answer("what is the overall rating?", ccn=None, conn=conn)
    assert out["kind"] == "need_ccn"
