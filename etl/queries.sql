-- ===========================================================================
-- Analytical SQL over the warehouse — the "consume the data" layer.
-- Demonstrates the joins + aggregation the role asks for. Runs on SQLite & PG.
-- Use with: sqlite3 etl/warehouse.db < etl/queries.sql   (or psql for Neon)
-- ===========================================================================

-- 1. Latest snapshot per facility (most recent CMS publish), with descriptive
--    attributes joined from the dimension. The "current scorecard" base view.
SELECT f.ccn,
       f.provider_name,
       f.state,
       f.certified_beds,
       s.overall_rating,
       s.completeness,
       s.qa_summary,
       s.processing_date
FROM   dim_facility f
JOIN   fact_report_snapshot s ON s.ccn = f.ccn
JOIN   (
         SELECT ccn, MAX(snapshot_date) AS latest
         FROM   fact_report_snapshot
         GROUP  BY ccn
       ) latest ON latest.ccn = s.ccn AND latest.latest = s.snapshot_date
ORDER  BY s.overall_rating DESC NULLS LAST, f.provider_name;

-- 2. Provider performance scorecard — rank facilities in a state by overall
--    rating, with a data-quality flag so low-confidence rows are visible.
SELECT f.provider_name,
       s.overall_rating,
       s.health_rating,
       s.staffing_rating,
       s.qm_rating,
       s.completeness,
       CASE WHEN s.completeness < 100 THEN 'review' ELSE 'ok' END AS dq_flag,
       RANK() OVER (ORDER BY s.overall_rating DESC) AS state_rank
FROM   dim_facility f
JOIN   fact_report_snapshot s ON s.ccn = f.ccn
WHERE  f.state = 'FL'
ORDER  BY state_rank;

-- 3. Rating trend for one facility over time (the historical-snapshot payoff).
SELECT snapshot_date,
       overall_rating,
       health_rating,
       staffing_rating,
       qm_rating,
       completeness
FROM   fact_report_snapshot
WHERE  ccn = '686123'
ORDER  BY snapshot_date;

-- 4. Run audit — recent pipeline executions and their outcomes.
SELECT run_id,
       kind,
       started_at,
       finished_at,
       attempted,
       succeeded,
       failed,
       status
FROM   ingestion_run
ORDER  BY started_at DESC
LIMIT  20;

-- 5. Data lineage — for each facility, the run + source that produced its data,
--    joining the granular log to its parent run. Answers "where did this come
--    from and when?" (the compliance/QA audit question).
SELECT l.ccn,
       l.status,
       l.processing_date          AS cms_publish_date,   -- data freshness
       l.snapshot_inserted,                               -- did it store new data?
       r.kind                     AS run_kind,
       r.started_at               AS run_time,
       l.source_urls                                      -- exact CMS API URLs called
FROM   ingestion_log l
JOIN   ingestion_run r ON r.run_id = l.run_id
ORDER  BY r.started_at DESC, l.ccn
LIMIT  50;
