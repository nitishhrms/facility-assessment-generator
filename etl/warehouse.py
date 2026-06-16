"""LOAD layer — writes the normalized report model into the SQL warehouse.

One codebase, two databases: SQLAlchemy lets the exact same SQL run on local
SQLite and on Neon PostgreSQL — only the DATABASE_URL changes.
"""

import json
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from etl.config import SCHEMA_PATH, database_url
from etl.field_map import DATASETS


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


def get_engine(url: Optional[str] = None) -> Engine:
    """Create a SQLAlchemy engine for SQLite (default) or Postgres/Neon."""
    return create_engine(url or database_url(), future=True)


def init_schema(engine: Engine) -> None:
    """Create tables/indexes if they don't exist (idempotent)."""
    ddl = SCHEMA_PATH.read_text(encoding="utf-8")
    with engine.begin() as conn:
        # SQLite/psycopg execute one statement at a time.
        for statement in [s.strip() for s in ddl.split(";") if s.strip()]:
            conn.execute(text(statement))


# --- Ingestion-run lifecycle (lineage backbone) ----------------------------

def start_run(engine: Engine, kind: str) -> str:
    run_id = _uuid()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ingestion_run (run_id, kind, started_at, status) "
                "VALUES (:run_id, :kind, :started_at, 'running')"
            ),
            {"run_id": run_id, "kind": kind, "started_at": _now()},
        )
    return run_id


def finish_run(engine: Engine, run_id: str, attempted: int, succeeded: int,
               failed: int, status: str = "complete") -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE ingestion_run SET finished_at=:f, attempted=:a, "
                "succeeded=:s, failed=:x, status=:st WHERE run_id=:run_id"
            ),
            {"f": _now(), "a": attempted, "s": succeeded, "x": failed,
             "st": status, "run_id": run_id},
        )


# --- Dimension + fact writes ------------------------------------------------

def upsert_facility(engine: Engine, report: dict) -> None:
    """Insert or update the facility dimension row."""
    params = {
        "ccn": report["ccn"],
        "provider_name": report["official_name"],
        "state": report["state"],
        "location": report["location"],
        "beds": int(report["certified_beds"]) if report.get("certified_beds") else None,
        "updated_at": _now(),
    }
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM dim_facility WHERE ccn=:ccn"), {"ccn": params["ccn"]}
        ).first()
        if exists:
            conn.execute(
                text(
                    "UPDATE dim_facility SET provider_name=:provider_name, state=:state, "
                    "location=:location, certified_beds=:beds, updated_at=:updated_at "
                    "WHERE ccn=:ccn"
                ),
                params,
            )
        else:
            conn.execute(
                text(
                    "INSERT INTO dim_facility (ccn, provider_name, state, location, "
                    "certified_beds, updated_at) VALUES (:ccn, :provider_name, :state, "
                    ":location, :beds, :updated_at)"
                ),
                params,
            )


def insert_snapshot(engine: Engine, report: dict, dq: dict,
                    run_id: Optional[str] = None) -> tuple[Optional[str], bool]:
    """Insert one dated snapshot. Returns (snapshot_id, inserted?).

    Incremental: if a snapshot already exists for this (ccn, processing_date),
    we skip the insert — this is the hook Phase C's scheduler relies on.
    """
    rm = report["rating_map"]
    processing_date = report.get("processing_date")

    with engine.begin() as conn:
        existing = conn.execute(
            text(
                "SELECT id FROM fact_report_snapshot "
                "WHERE ccn=:ccn AND processing_date IS :pd"
                if processing_date is None
                else "SELECT id FROM fact_report_snapshot WHERE ccn=:ccn AND processing_date=:pd"
            ),
            {"ccn": report["ccn"], "pd": processing_date},
        ).first()
        if existing:
            return existing[0], False

        snapshot_id = _uuid()
        conn.execute(
            text(
                "INSERT INTO fact_report_snapshot (id, ccn, snapshot_date, overall_rating, "
                "health_rating, staffing_rating, qm_rating, metrics, qa_summary, completeness, "
                "processing_date, source_datasets, run_id, created_at) VALUES (:id, :ccn, "
                ":snapshot_date, :overall, :health, :staffing, :qm, :metrics, :qa, :completeness, "
                ":pd, :sources, :run_id, :created_at)"
            ),
            {
                "id": snapshot_id,
                "ccn": report["ccn"],
                "snapshot_date": date.today().isoformat(),
                "overall": _int(rm.get("Overall Star Rating")),
                "health": _int(rm.get("Health Inspection")),
                "staffing": _int(rm.get("Staffing")),
                "qm": _int(rm.get("Quality of Resident Care")),
                "metrics": json.dumps(report["metrics"]),
                "qa": report["qa_summary"],
                "completeness": dq["completeness"] if dq else None,
                "pd": processing_date,
                "sources": json.dumps(DATASETS),
                "run_id": run_id,
                "created_at": _now(),
            },
        )
        return snapshot_id, True


def get_history(engine: Engine, ccn: str) -> list[dict]:
    """All snapshots for a facility, oldest first (the time series)."""
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT snapshot_date, overall_rating, health_rating, staffing_rating, "
                "qm_rating, completeness, qa_summary, processing_date "
                "FROM fact_report_snapshot WHERE ccn=:ccn "
                "ORDER BY snapshot_date ASC, created_at ASC"
            ),
            {"ccn": ccn},
        )
        return [dict(r._mapping) for r in rows]


# --- Lineage / logging ------------------------------------------------------

def insert_log(engine: Engine, run_id: Optional[str], entry: dict) -> None:
    """Write one granular audit row (per facility per run)."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ingestion_log (id, run_id, ccn, status, error, provider_found, "
                "claims_rows, completeness, processing_date, source_urls, snapshot_inserted, "
                "logged_at) VALUES (:id, :run_id, :ccn, :status, :error, :provider_found, "
                ":claims_rows, :completeness, :processing_date, :source_urls, :snapshot_inserted, "
                ":logged_at)"
            ),
            {
                "id": _uuid(),
                "run_id": run_id,
                "ccn": entry.get("ccn"),
                "status": entry.get("status"),
                "error": entry.get("error"),
                "provider_found": 1 if entry.get("provider_found") else 0,
                "claims_rows": entry.get("claims_rows"),
                "completeness": entry.get("completeness"),
                "processing_date": entry.get("processing_date"),
                "source_urls": json.dumps(entry.get("source_urls") or []),
                "snapshot_inserted": 1 if entry.get("snapshot_inserted") else 0,
                "logged_at": _now(),
            },
        )


def get_runs(engine: Engine, limit: int = 20) -> list[dict]:
    """Recent pipeline runs with their outcome counts."""
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT run_id, kind, started_at, finished_at, attempted, succeeded, failed, "
                "status FROM ingestion_run ORDER BY started_at DESC LIMIT :limit"
            ),
            {"limit": limit},
        )
        return [dict(r._mapping) for r in rows]


def get_run_log(engine: Engine, run_id: str) -> list[dict]:
    """The per-facility audit trail for one run (lineage)."""
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT ccn, status, error, completeness, processing_date, snapshot_inserted, "
                "source_urls FROM ingestion_log WHERE run_id=:run_id ORDER BY logged_at ASC"
            ),
            {"run_id": run_id},
        )
        return [dict(r._mapping) for r in rows]


# --- Watchlist (which facilities the scheduler refreshes) -------------------

def add_to_watchlist(engine: Engine, ccn: str, label: Optional[str] = None) -> bool:
    """Add a CCN to the watchlist. Returns False if it was already present."""
    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM watchlist WHERE ccn=:ccn"), {"ccn": ccn}
        ).first()
        if exists:
            return False
        conn.execute(
            text("INSERT INTO watchlist (ccn, label, added_at) VALUES (:ccn, :label, :added_at)"),
            {"ccn": ccn, "label": label, "added_at": _now()},
        )
        return True


def remove_from_watchlist(engine: Engine, ccn: str) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM watchlist WHERE ccn=:ccn"), {"ccn": ccn})


def get_watchlist(engine: Engine) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT ccn, label, added_at FROM watchlist ORDER BY added_at ASC")
        )
        return [dict(r._mapping) for r in rows]


def _int(v) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None
