-- ===========================================================================
-- Facility-report data warehouse — star schema.
-- Portable DDL: runs on SQLite (local dev) and PostgreSQL / Neon (production).
-- Surrogate keys are TEXT UUIDs (generated in Python) to stay dialect-neutral
-- instead of SERIAL vs AUTOINCREMENT. JSON is stored as TEXT (use JSONB on PG).
-- ===========================================================================

-- Dimension: one row per facility (latest known descriptive attributes).
CREATE TABLE IF NOT EXISTS dim_facility (
    ccn             TEXT PRIMARY KEY,
    provider_name   TEXT,
    state           TEXT,
    location        TEXT,
    certified_beds  INTEGER,
    updated_at      TEXT NOT NULL
);

-- Lineage / orchestration: one row per pipeline execution.
CREATE TABLE IF NOT EXISTS ingestion_run (
    run_id        TEXT PRIMARY KEY,
    kind          TEXT NOT NULL,            -- 'single' | 'batch' | 'scheduled'
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    attempted     INTEGER NOT NULL DEFAULT 0,
    succeeded     INTEGER NOT NULL DEFAULT 0,
    failed        INTEGER NOT NULL DEFAULT 0,
    status        TEXT NOT NULL DEFAULT 'running'   -- 'running' | 'complete' | 'error'
);

-- Fact: one row per facility per pull → historical snapshots / time series.
CREATE TABLE IF NOT EXISTS fact_report_snapshot (
    id               TEXT PRIMARY KEY,
    ccn              TEXT NOT NULL,
    snapshot_date    TEXT NOT NULL,         -- date the pipeline ran (yyyy-mm-dd)
    overall_rating   INTEGER,
    health_rating    INTEGER,
    staffing_rating  INTEGER,
    qm_rating        INTEGER,
    metrics          TEXT,                  -- JSON: the 12 metric lines + verdicts
    qa_summary       TEXT,
    completeness     INTEGER,               -- 0-100 (data-quality completeness %)
    processing_date  TEXT,                  -- CMS data freshness (lineage)
    source_datasets  TEXT,                  -- JSON: dataset ids used (lineage)
    run_id           TEXT,
    created_at       TEXT NOT NULL,
    FOREIGN KEY (ccn) REFERENCES dim_facility (ccn),
    FOREIGN KEY (run_id) REFERENCES ingestion_run (run_id),
    -- Incremental-refresh hook (Phase C): one snapshot per facility per CMS publish.
    UNIQUE (ccn, processing_date)
);

CREATE INDEX IF NOT EXISTS ix_snapshot_ccn  ON fact_report_snapshot (ccn);
CREATE INDEX IF NOT EXISTS ix_snapshot_date ON fact_report_snapshot (snapshot_date);

-- Watchlist: the set of facilities the scheduled refresh keeps up to date.
CREATE TABLE IF NOT EXISTS watchlist (
    ccn       TEXT PRIMARY KEY,
    label     TEXT,
    added_at  TEXT NOT NULL
);

-- Lineage / logging: one row per facility per run — the granular audit trail.
-- Answers "what happened to this CCN in this run, and where did the data come from?"
CREATE TABLE IF NOT EXISTS ingestion_log (
    id                 TEXT PRIMARY KEY,
    run_id             TEXT,
    ccn                TEXT,
    status             TEXT,        -- 'ok' | 'notfound' | 'error'
    error              TEXT,
    provider_found     INTEGER,     -- 0/1
    claims_rows        INTEGER,
    completeness       INTEGER,
    processing_date    TEXT,        -- CMS publish date the data came from (lineage)
    source_urls        TEXT,        -- JSON list of the exact CMS API URLs called (lineage)
    snapshot_inserted  INTEGER,     -- 0/1 (incremental: 1 only when new data stored)
    logged_at          TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES ingestion_run (run_id)
);

CREATE INDEX IF NOT EXISTS ix_log_run ON ingestion_log (run_id);
CREATE INDEX IF NOT EXISTS ix_log_ccn ON ingestion_log (ccn);
