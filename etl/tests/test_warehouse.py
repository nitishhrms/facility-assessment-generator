"""Warehouse tests — run against an in-memory/temp SQLite DB (no network)."""

import tempfile
from pathlib import Path

from etl.tests.fixtures import AVERAGES, CLAIMS, PROVIDER
from etl.transform import build_report, data_quality
from etl.warehouse import (
    finish_run,
    get_engine,
    get_history,
    init_schema,
    insert_snapshot,
    start_run,
    upsert_facility,
)


def _fresh_engine():
    tmp = Path(tempfile.mkdtemp()) / "test.db"
    engine = get_engine(f"sqlite:///{tmp.as_posix()}")
    init_schema(engine)
    return engine


def test_snapshot_insert_and_history():
    engine = _fresh_engine()
    report = build_report(PROVIDER, CLAIMS, AVERAGES)
    dq = data_quality(report)
    run_id = start_run(engine, "single")

    upsert_facility(engine, report)
    _id, inserted = insert_snapshot(engine, report, dq, run_id)
    finish_run(engine, run_id, 1, 1, 0)

    assert inserted is True
    history = get_history(engine, "686123")
    assert len(history) == 1
    assert history[0]["overall_rating"] == 5
    assert history[0]["completeness"] == 100


def test_incremental_skip_same_processing_date():
    engine = _fresh_engine()
    report = build_report(PROVIDER, CLAIMS, AVERAGES)
    dq = data_quality(report)
    run_id = start_run(engine, "single")
    upsert_facility(engine, report)

    _id1, inserted1 = insert_snapshot(engine, report, dq, run_id)
    _id2, inserted2 = insert_snapshot(engine, report, dq, run_id)  # same processing_date

    assert inserted1 is True
    assert inserted2 is False  # incremental refresh: no duplicate snapshot
    assert len(get_history(engine, "686123")) == 1


def test_new_snapshot_when_processing_date_changes():
    engine = _fresh_engine()
    report = build_report(PROVIDER, CLAIMS, AVERAGES)
    dq = data_quality(report)
    run_id = start_run(engine, "single")
    upsert_facility(engine, report)
    insert_snapshot(engine, report, dq, run_id)

    newer = dict(report)
    newer["processing_date"] = "2026-06-01"  # CMS published new data
    _id, inserted = insert_snapshot(engine, newer, dq, run_id)

    assert inserted is True
    assert len(get_history(engine, "686123")) == 2
