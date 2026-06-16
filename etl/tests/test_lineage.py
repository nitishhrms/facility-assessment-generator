"""Lineage / logging tests (temp SQLite + URL builder — no network)."""

import tempfile
from pathlib import Path

from etl.cms_client import query_url
from etl.warehouse import (
    finish_run,
    get_engine,
    get_run_log,
    get_runs,
    init_schema,
    insert_log,
    start_run,
)


def _fresh_engine():
    tmp = Path(tempfile.mkdtemp()) / "lin.db"
    engine = get_engine(f"sqlite:///{tmp.as_posix()}")
    init_schema(engine)
    return engine


def test_query_url_carries_lineage():
    url = query_url("provider", "686123")
    assert "4pq5-n9py" in url                       # dataset id (source)
    assert "cms_certification_number_ccn" in url     # the filter property
    assert "686123" in url                           # the CCN queried


def test_log_and_read_back():
    engine = _fresh_engine()
    run_id = start_run(engine, "batch")
    insert_log(engine, run_id, {
        "ccn": "686123", "status": "ok", "provider_found": True, "claims_rows": 4,
        "completeness": 100, "processing_date": "2026-05-01", "snapshot_inserted": True,
        "source_urls": [query_url("provider", "686123"), query_url("claims", "686123")],
    })
    insert_log(engine, run_id, {
        "ccn": "999999", "status": "notfound", "provider_found": False,
        "source_urls": [query_url("provider", "999999")],
    })
    finish_run(engine, run_id, 2, 1, 1)

    runs = get_runs(engine)
    assert runs[0]["attempted"] == 2 and runs[0]["succeeded"] == 1 and runs[0]["failed"] == 1

    log = get_run_log(engine, run_id)
    assert [e["ccn"] for e in log] == ["686123", "999999"]
    assert log[0]["snapshot_inserted"] == 1
    assert log[1]["status"] == "notfound"
    assert "4pq5-n9py" in log[0]["source_urls"]   # lineage persisted
