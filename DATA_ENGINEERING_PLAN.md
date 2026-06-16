# Data Engineering Plan — Facility Assessment Report Generator

> Roadmap for turning the current single-record, in-memory tool into a small but
> real **data pipeline**: batch ingestion, a persisted warehouse with historical
> snapshots, scheduled/incremental refresh with caching, and data lineage/logging.
>
> Audience: us, working through it together — written to be **understood**, not
> just executed. Each phase explains *what*, *why*, *how*, and *how we verify it*.

---

## 0. Where we are today (the baseline)

```
Browser (React) ──/api/cms──► Netlify Function (stateless proxy) ──► CMS API
        │
        └─ buildReport()  (pure transform: join 3 datasets → 1 report model)
        └─ dataQuality()  (pure validation: completeness / freshness / missing)
        └─ exportPdf / exportDocx  (one report at a time)
```

**What already counts as data engineering** (we keep all of it):
- **Extraction** — `netlify/functions/cms.js` does filtered, server-side API pulls.
- **Integration/joins** — `buildReport()` joins Provider + Claims + Averages on CCN
  and `state_or_nation`.
- **Schema mapping** — `src/config/fieldMap.js` maps cryptic CMS columns → clean labels.
- **Transformation** — `buildReport()` normalizes types, units, decimals into one model.
- **Data quality** — `dataQuality()` computes completeness %, freshness, missing flags.
- **Tests** — 25 Vitest unit tests over the pure functions.

**The four gaps this plan closes:**
1. No persistence / warehouse / historical snapshots.
2. One record at a time — no batch/bulk processing.
3. No scheduling / orchestration / incremental refresh / caching.
4. No data lineage / logging beyond inline errors.

**Guiding principle:** `buildReport()` and `dataQuality()` are already pure
functions. They become the **shared transform core** reused by the live UI, the
batch pipeline, and the scheduled job. We extend the architecture; we do not
rewrite it.

---

## Target architecture (end state)

```
                         ┌──────────────────────────────────────────┐
   CSV of CCNs ──────────►  BATCH FUNCTION  (netlify/functions/batch) │
                         │   extract → transform → validate → write   │
   Live single lookup ───►  (existing /api/cms path, unchanged UX)    │
                         └───────────────┬──────────────────────────┘
                                         │ upsert
   CRON (scheduled fn) ──► ORCHESTRATOR ─┤  (incremental: only if processing_date changed)
   load watchlist → loop  │              ▼
                          │   ┌────────────────────────────────────┐
                          │   │  NEON POSTGRES (warehouse)          │
   averages cache ◄───────┘   │  dim_facility / fact_report_snapshot│
   (Netlify Blobs, TTL)       │  ingestion_run / ingestion_log      │  ← lineage + logging
                              └────────────────────────────────────┘
                                         │ read
                              History / trend / run-log views in UI
```

---

## Phase A — Batch / bulk processing  *(no database yet)*

**Goal:** upload a CSV of CCNs → get a report for every facility in one run.

**Why first:** highest value, lowest risk, needs no new infrastructure, and it is
the feature originally requested. It also forces us to make extraction *reusable*
and *concurrency-safe*, which every later phase depends on.

### What we build
- `netlify/functions/batch.js` — accepts `{ ccns: [...] }`, returns
  `[{ ccn, status, report?, error? }]`.
  - Fetches the **averages dataset once per run** (today it is re-fetched on every
    single lookup — this is an immediate efficiency win and a shared "dimension").
  - Loops provider + claims extraction through a **concurrency pool (~5 in flight)**
    to respect CMS rate limits.
  - **Partial-failure handling:** each CCN resolves to `ok | notfound | error`; one
    bad row never aborts the run.
- `src/lib/batch.js` (client) — parse CSV → call the function → assemble outputs.
- `src/components/CsvBatchUpload.jsx` — file drop, progress, results table.
- **Outputs:**
  - a **ZIP** of per-facility PDF (and/or Word) reports — add `jszip`.
  - a **roll-up CSV**: `ccn, name, state, overall_rating, qa_summary, completeness, status, error`.

### Key decisions to make in this phase
- CSV format: single `ccn` column vs. allowing manual-input columns (EMR, census…) per row.
- Concurrency limit and per-request timeout.
- Output default: ZIP of PDFs, the summary CSV, or both.

### How we verify
- Unit tests: CSV parser, concurrency pool, roll-up CSV builder.
- A mixed fixture (valid CCN + unknown CCN + malformed) → assert statuses are correct
  and the run completes.

### Files touched
`+ netlify/functions/batch.js`, `+ src/lib/batch.js`,
`+ src/components/CsvBatchUpload.jsx`, `~ src/App.jsx`, `~ package.json` (jszip),
`+ tests`.

---

## Phase B — Persistence / warehouse / historical snapshots  *(Neon Postgres)*

**Goal:** every report we generate (live or batch) can be **saved as a dated
snapshot** and queried later — turning one-shot reports into time series.

**Why second:** batch now produces many records; persisting them is the natural
next step and unlocks history/trends. Neon is already initialized (`.netlify/db`).

### Schema (small star schema)
```
dim_facility
  ccn            text PK
  provider_name  text
  state          text
  address        text
  certified_beds int
  updated_at     timestamptz

fact_report_snapshot
  id             bigserial PK
  ccn            text  FK → dim_facility
  snapshot_date  date            -- one row per CCN per pull → HISTORY
  overall_rating int
  health_rating  int
  staffing_rating int
  qm_rating      int
  metrics        jsonb           -- the 12 metric lines + verdicts
  qa_summary     text
  completeness   int
  processing_date date           -- CMS data freshness (lineage)
  run_id         bigint FK → ingestion_run
  created_at     timestamptz
  UNIQUE (ccn, processing_date)  -- incremental refresh hook (Phase C)

ingestion_run                    -- also the backbone of Phase D lineage
  run_id         bigserial PK
  kind           text            -- 'live' | 'batch' | 'scheduled'
  started_at / finished_at timestamptz
  attempted / ok / failed int
  status         text
```

### What we build
- `netlify/functions/db.js` — Neon client (`@netlify/neon`), connection + helpers.
- `src/lib/warehouse.js` (server-side) — `upsertFacility()`, `insertSnapshot()`,
  `getHistory(ccn)`, `startRun()/finishRun()`.
- A migration file (`db/schema.sql`) + a `npm run db:migrate` script.
- Wire **batch** (and optionally live) to write a snapshot per successful record.
- Read endpoint `netlify/functions/history.js` + UI tab **Facility History**
  (rating/metric trend over snapshot_date via the existing Recharts).

### How we verify
- Run migration → insert two snapshots for one CCN with different `processing_date`
  → assert `getHistory` returns both in order.
- Test the `report model → row` mapper as a pure function (no DB needed).

### Files touched
`+ db/schema.sql`, `+ netlify/functions/db.js`, `+ src/lib/warehouse.js`,
`+ netlify/functions/history.js`, `+ src/components/FacilityHistory.jsx`,
`~ batch.js`, `~ package.json` (`@netlify/neon`), `~ netlify.toml`, `+ tests`.

---

## Phase C — Scheduling / orchestration / incremental refresh / caching

**Goal:** the warehouse refreshes itself on a schedule, cheaply.

**Why third:** needs the warehouse (B) to write into and the batch core (A) to reuse.

### What we build
- **Watchlist** — a table or config of CCNs to track (`watchlist(ccn, added_at)`).
- **Scheduled Function** `netlify/functions/refresh-scheduled.js` with a cron in
  `netlify.toml` (e.g. nightly). This is the **orchestrator**:
  `load watchlist → batch-extract → transform → validate → upsert snapshot → record run`.
- **Incremental refresh** — skip writing a snapshot when CMS `processing_date` is
  unchanged since the latest stored one (the `UNIQUE(ccn, processing_date)` from B).
  Cheap, idempotent, no duplicate history.
- **Caching** — cache the slow-changing **averages** dataset (Netlify Blobs, TTL
  ~24h) so live + batch + scheduled all skip that fetch. Optional per-CCN short TTL.

### How we verify
- Run the orchestrator twice back-to-back → second run writes **0** new snapshots
  (incremental works) and `ingestion_run` shows the skip counts.
- Cache hit/miss assertions on the averages loader.

### Files touched
`+ netlify/functions/refresh-scheduled.js`, `+ src/lib/cache.js`,
`+ db/watchlist.sql`, `~ netlify.toml` (`[functions."refresh-scheduled"]` schedule),
`~ cms extraction to use cache`, `+ tests`.

---

## Phase D — Data lineage / logging

**Goal:** for any number in the warehouse, answer *where did it come from, when,
from which dataset, in which run* — and make runs observable.

**Why last:** it annotates and reports on everything B and C produce.

### What we build
- **Lineage columns/table** — persist with each snapshot: source dataset IDs, the
  upstream query URL, CMS `processing_date`, `fetched_at`, and `run_id`
  (most of this already lands via B's schema; D completes it).
- `ingestion_log` (per CCN per run): `run_id, ccn, dataset, http_status, row_count,
  status, error` — the granular trail.
- **Structured JSON logging** in the functions (replace inline string errors) so
  Netlify function logs are queryable.
- **Run history view** in the UI: list recent runs, their counts/status, and
  drill into per-CCN logs.

### How we verify
- A batch run with one failing CCN → `ingestion_log` has the error row with the
  source URL and status; the run summary counts match.

### Files touched
`+ db/lineage.sql` (or extend B), `~ all functions (structured logger)`,
`+ src/lib/logger.js`, `+ netlify/functions/runs.js`,
`+ src/components/RunHistory.jsx`, `+ tests`.

---

## Cross-cutting notes

- **Env / secrets:** Neon connection string via Netlify env vars
  (`NETLIFY_DATABASE_URL`); never committed. We'll document setup in the README.
- **Local dev:** the existing Vite middleware mocks `/api/cms`; we extend it (or use
  `netlify dev`) to also serve `batch` / `history` / `runs` locally.
- **Testing:** keep the pure-function discipline — mappers and validators stay pure
  and unit-tested; DB/HTTP stays in thin adapters. Extend the current Vitest suite.
- **Docs:** update `README.md` (features) and `SYSTEM_DESIGN.md` (architecture) as
  each phase lands; move shipped items out of "Possible extensions (not built)".
- **Backups:** a fresh zip backup was taken before this work began.

---

## Execution checklist

- [x] **Phase A** — batch in the React web app: CSV upload / paste UI (`BatchUpload.jsx`),
      bounded-concurrency engine reusing `buildReport` (`batch.js`), ZIP of PDFs + roll-up
      summary CSV, partial-failure handling. `exportPdf` refactored to `buildPdfDoc` (reused
      for the ZIP). 33 JS tests pass (incl. CSV parsing, summary CSV, real ZIP round-trip);
      `npm run build` green.
- [x] **Phase B** — SQL warehouse **built in Python** under `etl/` (Neon-ready, SQLite by default):
      star schema (`schema.sql`), extract/transform/load (`cms_client`/`transform`/`warehouse`),
      CLI orchestrator (`pipeline.py`), PDF output (`pdf_report.py`), analytical SQL
      (`queries.sql`), 11 passing tests. Also delivers the **Python component** and
      seeds batch (`--csv`), incremental refresh, and run/lineage logging.
      _Remaining for full Phase B: optional Neon provisioning + a history view in the React UI._
- [x] **Phase C** — built in `etl/`: `watchlist` table + CLI (`--watch-add/-list/-import/-remove`),
      orchestrator (`--refresh`), interval scheduler (`scheduler.py`) + OS-cron docs, TTL
      caching of the averages dataset (`cache.py`, `--no-cache`/`--clear-cache`), and
      incremental refresh (snapshot only on new CMS `processing_date`). 15 passing tests
      (incl. cache miss/hit/expiry + watchlist). Verified live: cache miss→hit, incremental skip.
- [x] **Phase D** — built in `etl/`: `ingestion_log` table (per-facility audit trail with
      `source_urls` + CMS freshness), structured JSON logging (`logger.py` → `etl/.logs/`),
      run-history + lineage CLI (`--runs`, `--run-log`), lineage SQL in `queries.sql`.
      17 passing tests (incl. lineage). Verified live: run log + source-URL trail + JSON log.
      _Optional remaining: surface run history inside the React web UI (needs the app to
      read the warehouse via a backend endpoint)._
- [ ] Docs updated (README + SYSTEM_DESIGN) per phase
```
