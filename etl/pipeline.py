"""Pipeline orchestrator (CLI).

Wires the ETL stages together for one CCN or a CSV batch:

    extract (CMS API) -> transform (report model + QA) -> load (warehouse) -> PDF

Examples:
    python -m etl.pipeline --ccn 686123 --pdf
    python -m etl.pipeline --csv ccns.csv --pdf --out-dir reports
    python -m etl.pipeline --history 686123
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from etl import cms_client
from etl.cache import cached_json, clear_cache
from etl.config import AVERAGES_CACHE_TTL, DEFAULT_OUTPUT_DIR, database_url
from etl.field_map import DATASETS
from etl.logger import get_logger, log_event
from etl.transform import build_report, data_quality
from etl.warehouse import (
    add_to_watchlist,
    finish_run,
    get_engine,
    get_history,
    get_run_log,
    get_runs,
    get_watchlist,
    init_schema,
    insert_log,
    insert_snapshot,
    remove_from_watchlist,
    start_run,
    upsert_facility,
)


def load_averages(use_cache: bool = True) -> list[dict]:
    """Fetch the averages dataset, using the TTL cache unless disabled."""
    if not use_cache:
        return cms_client.fetch_averages()
    data, status = cached_json(
        f"averages_{DATASETS['averages']}", AVERAGES_CACHE_TTL, cms_client.fetch_averages
    )
    print(f"Averages cache: {status}")
    return data


def _read_ccns_from_csv(path: str) -> list[str]:
    """Read the 'ccn' column (or the first column) from a CSV of facilities."""
    ccns: list[str] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames and any(f.strip().lower() == "ccn" for f in reader.fieldnames):
            key = next(f for f in reader.fieldnames if f.strip().lower() == "ccn")
            ccns = [row[key].strip() for row in reader if row.get(key, "").strip()]
        else:
            fh.seek(0)
            ccns = [line.strip() for line in fh if line.strip() and line.strip().lower() != "ccn"]
    return ccns


def process_one(engine, ccn: str, averages: list[dict], run_id: str,
                make_pdf: bool, out_dir: Path, logger=None) -> dict:
    """Extract+transform+load a single CCN. Never raises — returns a status dict.

    Also records lineage: the exact CMS URLs queried, the CMS publish date, and
    whether a new snapshot was stored — written to ingestion_log + the JSON log.
    """
    # Lineage: the exact source URLs this facility's data comes from.
    source_urls = [cms_client.query_url("provider", ccn), cms_client.query_url("claims", ccn)]
    result = {"ccn": ccn, "status": "error", "provider_found": False,
              "claims_rows": 0, "completeness": None, "processing_date": None,
              "snapshot_inserted": False, "source_urls": source_urls, "error": None}
    try:
        provider = cms_client.fetch_provider(ccn)
        if not provider:
            result["status"] = "notfound"
        else:
            result["provider_found"] = True
            claims = cms_client.fetch_claims(ccn)
            result["claims_rows"] = len(claims)
            report = build_report(provider, claims, averages)
            dq = data_quality(report)

            upsert_facility(engine, report)
            _id, inserted = insert_snapshot(engine, report, dq, run_id)

            result.update(
                status="ok",
                name=report["name"],
                completeness=dq["completeness"],
                qa_summary=report["qa_summary"],
                processing_date=report["processing_date"],
                snapshot_inserted=inserted,
                snapshot="inserted" if inserted else "skipped (already current)",
            )
            if make_pdf:
                from etl.pdf_report import generate_pdf
                pdf_path = out_dir / f"{ccn}_{report['name'][:40].strip().replace(' ', '_')}.pdf"
                generate_pdf(report, dq, pdf_path)
                result["pdf"] = str(pdf_path)
    except Exception as exc:  # noqa: BLE001 — partial-failure handling
        result["status"] = "error"
        result["error"] = str(exc)

    # Persist the granular audit row + structured log event (lineage/logging).
    insert_log(engine, run_id, result)
    if logger:
        log_event(logger, "facility_processed", ccn=ccn, status=result["status"],
                  completeness=result["completeness"], snapshot_inserted=result["snapshot_inserted"],
                  error=result["error"])
    return result


def run(ccns: list[str], kind: str, make_pdf: bool, out_dir: Path,
        use_cache: bool = True) -> list[dict]:
    engine = get_engine()
    init_schema(engine)
    run_id = start_run(engine, kind)
    logger = get_logger()
    log_event(logger, "run_start", run_id=run_id, kind=kind, facilities=len(ccns))

    print(f"Warehouse: {database_url()}")
    print(f"Run {run_id} ({kind}) — {len(ccns)} facilit(y/ies)\n")

    averages = load_averages(use_cache)  # fetched ONCE (cached across runs), reused per CCN
    results = [process_one(engine, c, averages, run_id, make_pdf, out_dir, logger) for c in ccns]

    ok = len([r for r in results if r["status"] == "ok"])
    failed = len([r for r in results if r["status"] in ("error", "notfound")])
    finish_run(engine, run_id, len(ccns), ok, failed)
    log_event(logger, "run_finish", run_id=run_id, attempted=len(ccns), ok=ok, failed=failed)

    for r in results:
        line = f"  [{r['status']:>8}] {r['ccn']}"
        if r["status"] == "ok":
            line += f"  {r.get('name', '')}  ({r['completeness']}% complete, {r['snapshot']})"
        elif r["status"] == "error":
            line += f"  {r['error']}"
        print(line)
    print(f"\nDone: {ok} ok, {failed} failed.")
    return results


def show_history(ccn: str) -> None:
    engine = get_engine()
    init_schema(engine)
    rows = get_history(engine, ccn)
    if not rows:
        print(f"No snapshots stored for CCN {ccn} yet.")
        return
    print(f"History for {ccn} ({len(rows)} snapshot(s)):")
    for r in rows:
        print(
            f"  {r['snapshot_date']}  overall={r['overall_rating']}  "
            f"completeness={r['completeness']}%  freshness={r['processing_date']}"
        )


def show_runs(limit: int = 20) -> None:
    engine = get_engine()
    init_schema(engine)
    runs = get_runs(engine, limit)
    if not runs:
        print("No runs recorded yet.")
        return
    print(f"Recent runs ({len(runs)}):")
    for r in runs:
        print(
            f"  {r['started_at'][:19]}  {r['kind']:<9} "
            f"attempted={r['attempted']} ok={r['succeeded']} failed={r['failed']} "
            f"[{r['status']}]  {r['run_id']}"
        )


def show_run_log(run_id: str) -> None:
    """Per-facility audit trail for one run, including data-source lineage."""
    engine = get_engine()
    init_schema(engine)
    rows = get_run_log(engine, run_id)
    if not rows:
        print(f"No log entries for run {run_id}.")
        return
    print(f"Audit log for run {run_id} ({len(rows)} facilit(y/ies)):")
    for r in rows:
        line = (f"  [{r['status']:>8}] {r['ccn']}  freshness={r['processing_date']}  "
                f"snapshot={'new' if r['snapshot_inserted'] else 'unchanged'}")
        if r["status"] == "error":
            line += f"  error={r['error']}"
        print(line)
        urls = json.loads(r["source_urls"] or "[]")
        for u in urls:
            print(f"        source: {u}")


def refresh_watchlist(make_pdf: bool, out_dir: Path, use_cache: bool = True) -> list[dict]:
    """Orchestrator: refresh every facility on the watchlist (used by the scheduler)."""
    engine = get_engine()
    init_schema(engine)
    ccns = [w["ccn"] for w in get_watchlist(engine)]
    if not ccns:
        print("Watchlist is empty — add CCNs with --watch-add first.")
        return []
    return run(ccns, "scheduled", make_pdf, out_dir, use_cache)


def manage_watchlist(add: list[str] | None, remove: list[str] | None,
                     import_csv: str | None, show: bool) -> None:
    engine = get_engine()
    init_schema(engine)
    if import_csv:
        add = (add or []) + _read_ccns_from_csv(import_csv)
    for ccn in add or []:
        print(("added  " if add_to_watchlist(engine, ccn) else "exists ") + ccn)
    for ccn in remove or []:
        remove_from_watchlist(engine, ccn)
        print("removed " + ccn)
    if show or not (add or remove or import_csv):
        wl = get_watchlist(engine)
        print(f"Watchlist ({len(wl)}):")
        for w in wl:
            print(f"  {w['ccn']}  {w.get('label') or ''}".rstrip())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Facility-report ETL pipeline.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ccn", help="Process a single CCN.")
    group.add_argument("--csv", help="Process a CSV file of CCNs (column 'ccn').")
    group.add_argument("--history", help="Print stored snapshot history for a CCN.")
    group.add_argument("--refresh", action="store_true",
                       help="Refresh every facility on the watchlist (scheduled run).")
    group.add_argument("--watch-add", nargs="+", metavar="CCN",
                       help="Add one or more CCNs to the watchlist.")
    group.add_argument("--watch-remove", nargs="+", metavar="CCN",
                       help="Remove one or more CCNs from the watchlist.")
    group.add_argument("--watch-import", metavar="CSV",
                       help="Add all CCNs from a CSV to the watchlist.")
    group.add_argument("--watch-list", action="store_true", help="Show the watchlist.")
    group.add_argument("--runs", action="store_true", help="Show recent pipeline runs.")
    group.add_argument("--run-log", metavar="RUN_ID",
                       help="Show the per-facility audit trail (lineage) for a run.")
    group.add_argument("--clear-cache", action="store_true", help="Delete cached datasets.")
    parser.add_argument("--pdf", action="store_true", help="Also generate PDF report(s).")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR), help="PDF output dir.")
    parser.add_argument("--no-cache", action="store_true",
                        help="Bypass the averages cache (always re-download).")
    args = parser.parse_args(argv)

    use_cache = not args.no_cache
    out_dir = Path(args.out_dir)

    if args.clear_cache:
        print(f"Cleared {clear_cache()} cache file(s).")
        return 0
    if args.history:
        show_history(args.history)
        return 0
    if args.runs:
        show_runs()
        return 0
    if args.run_log:
        show_run_log(args.run_log)
        return 0
    if args.watch_add or args.watch_remove or args.watch_import or args.watch_list:
        manage_watchlist(args.watch_add, args.watch_remove, args.watch_import, args.watch_list)
        return 0
    if args.refresh:
        refresh_watchlist(args.pdf, out_dir, use_cache)
        return 0
    if args.ccn:
        run([args.ccn], "single", args.pdf, out_dir, use_cache)
    else:
        ccns = _read_ccns_from_csv(args.csv)
        if not ccns:
            print(f"No CCNs found in {args.csv}", file=sys.stderr)
            return 1
        run(ccns, "batch", args.pdf, out_dir, use_cache)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
