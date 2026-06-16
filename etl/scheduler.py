"""Scheduler — runs the watchlist refresh automatically on an interval.

Two ways to schedule in production:
  1. This script (a simple long-running loop) — good for a demo or a always-on box:
         python -m etl.scheduler --interval-hours 24
     Run it once and stop (for testing / a real OS scheduler):
         python -m etl.scheduler --once

  2. The OS scheduler (recommended for production) calling the pipeline directly:
       - Linux/macOS cron (every day at 6am):
             0 6 * * *  cd /path/to/project && python -m etl.pipeline --refresh
       - Windows Task Scheduler (daily): create a Basic Task that runs
             python -m etl.pipeline --refresh
         in the project directory.

Both paths call the same orchestrator: refresh every facility on the watchlist,
fetch averages from cache, and write a snapshot only when CMS data changed
(incremental refresh).
"""

import argparse
import time
from datetime import datetime
from pathlib import Path

from etl.config import DEFAULT_OUTPUT_DIR
from etl.pipeline import refresh_watchlist


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Scheduled watchlist refresher.")
    parser.add_argument("--interval-hours", type=float, default=24.0,
                        help="Hours between refreshes (default 24).")
    parser.add_argument("--once", action="store_true",
                        help="Run a single refresh and exit (for testing / OS cron).")
    parser.add_argument("--pdf", action="store_true", help="Also generate PDFs each run.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir)

    while True:
        print(f"\n=== Scheduled refresh @ {datetime.now().isoformat(timespec='seconds')} ===")
        refresh_watchlist(args.pdf, out_dir)
        if args.once:
            return 0
        print(f"Sleeping {args.interval_hours}h until next refresh…")
        time.sleep(args.interval_hours * 3600)


if __name__ == "__main__":
    raise SystemExit(main())
