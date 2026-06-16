# Python ETL Pipeline — Facility Report Warehouse

A Python data pipeline that **extracts** facility data from the public CMS
Provider Data Catalog API, **transforms** it into one normalized report model
(with QA benchmark verdicts and data-quality scoring), **loads** dated snapshots
into a **SQL warehouse**, and renders **executive-ready PDFs** — for one facility
or a CSV batch of many.

It is the Python/SQL counterpart to the React app in the repo root, reusing the
exact same business logic so the live UI and the automated pipeline stay in sync.

```
CMS API ──extract──► transform (report + QA) ──load──► SQL warehouse ──► PDF
 (requests)          (pure functions)         (SQLAlchemy)   (SQLite/Neon)  (fpdf2)
```

## Why this exists (mapping to the role)

| Skill the role asks for | Where it lives here |
|---|---|
| **SQL / warehouse, join disparate datasets** | `schema.sql` (star schema), `queries.sql` (joins, window functions, scorecards), `warehouse.py` |
| **Python automation** | the whole pipeline; `pipeline.py` CLI |
| **Generate PDF/document outputs** | `pdf_report.py` (fpdf2) |
| **API & public dataset integration** | `cms_client.py` |
| **QA / compliance data** | `transform.py` — benchmark verdicts + `data_quality()` |
| **Eliminate manual work / batch** | `--csv` batch mode, fetch-averages-once, partial-failure handling |
| **Data lineage / logging** | `ingestion_run` table + `source_datasets` per snapshot |

## Setup

```bash
cd etl
pip install -r requirements.txt
```

By default the warehouse is a local SQLite file (`etl/warehouse.db`) — **zero
setup**. To use Neon Postgres instead, set a connection string and install a
driver:

```bash
pip install "psycopg[binary]"
export DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require"
```

The same code runs against either database.

## Usage

Run from the **project root** (so `etl` is importable as a package):

```bash
# One facility — store a snapshot + write a PDF
python -m etl.pipeline --ccn 686123 --pdf

# Batch — a CSV of CCNs (column 'ccn'); writes one snapshot + PDF per facility
python -m etl.pipeline --csv etl/sample_ccns.csv --pdf --out-dir etl_output

# Show the stored snapshot history (time series) for a facility
python -m etl.pipeline --history 686123
```

### Automation (Phase C): watchlist + scheduled refresh + caching

```bash
# Maintain a watchlist of facilities to keep up to date
python -m etl.pipeline --watch-add 686123 015009
python -m etl.pipeline --watch-list
python -m etl.pipeline --watch-import etl/sample_ccns.csv

# Refresh the whole watchlist once (the orchestrator)
python -m etl.pipeline --refresh

# Run on a timer (long-running), or once for an OS scheduler / testing
python -m etl.scheduler --interval-hours 24
python -m etl.scheduler --once

# Cache controls (averages dataset is cached for 24h by default)
python -m etl.pipeline --refresh --no-cache   # bypass cache
python -m etl.pipeline --clear-cache          # delete cached datasets
```

**Production scheduling** — point the OS scheduler at the orchestrator:

```
# Linux/macOS cron — daily at 6am
0 6 * * *  cd /path/to/project && python -m etl.pipeline --refresh

# Windows Task Scheduler — a daily Basic Task running, in the project dir:
python -m etl.pipeline --refresh
```

**How the automation saves work:**
- **Caching** — the slow-changing state/national averages are cached (24h TTL), so
  repeat runs print `Averages cache: hit` and skip the download.
- **Incremental refresh** — a snapshot is written only when CMS publishes new data
  (a new `processing_date`); otherwise the run reports `skipped (already current)`.
  Re-running is therefore cheap and safe.

### Lineage & audit (Phase D): who ran what, and where did the data come from

```bash
# The "flight log" — recent runs with their ok/failed counts
python -m etl.pipeline --runs

# The per-facility audit trail for one run: status, CMS freshness date,
# whether new data was stored, and the EXACT CMS API URLs queried (lineage)
python -m etl.pipeline --run-log <RUN_ID>
```

- Every run writes a row to `ingestion_run`; every facility writes a row to
  `ingestion_log` (status, error, completeness, CMS `processing_date`, the exact
  `source_urls` called, and whether a snapshot was newly stored).
- Every event is also appended as one JSON line to `etl/.logs/pipeline-YYYY-MM-DD.log`
  — machine-queryable (grep/jq or load into a table), unlike loose console output.
- This is the **compliance/QA audit answer**: for any stored number you can trace
  the run, the time, the CMS publish date, and the source URL it came from.

## Inspect the warehouse with SQL

```bash
sqlite3 etl/warehouse.db < etl/queries.sql      # local
# or, on Neon:  psql "$DATABASE_URL" -f etl/queries.sql
```

`queries.sql` includes: latest snapshot per facility, a state performance
scorecard (window-function rank + data-quality flag), a single-facility rating
trend, and a run/lineage audit.

## Tests

```bash
python -m pytest etl -q
```

Covers the pure transform/QA logic (offline fixtures) and the warehouse
insert/history/incremental-refresh behavior (temp SQLite — no network).

## Schema (star schema)

- `dim_facility` — one row per facility (descriptive attributes).
- `fact_report_snapshot` — one row per facility **per CMS publish** → history /
  trends. `UNIQUE (ccn, processing_date)` powers incremental refresh.
- `ingestion_run` — one row per pipeline execution (lineage / audit).

## Notes

- **Incremental refresh:** re-running for the same `processing_date` does not
  duplicate a snapshot (`insert_snapshot` returns `inserted=False`). A new CMS
  publish (new `processing_date`) creates a new historical row.
- **Partial failure:** in batch mode, an invalid/unknown CCN is recorded as
  `notfound`/`error` and the run continues.
