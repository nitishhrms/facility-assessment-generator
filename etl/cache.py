"""A tiny file-based cache with time-to-live (TTL).

Used to avoid re-downloading slow-changing data (the CMS state/national averages
dataset) on every pipeline run. A cache entry is just a JSON file; if it is newer
than its TTL we reuse it, otherwise we re-fetch and rewrite it.
"""

import json
import time
from pathlib import Path
from typing import Callable

from etl.config import ETL_DIR

CACHE_DIR = ETL_DIR / ".cache"


def cached_json(key: str, ttl_seconds: int, fetch_fn: Callable[[], object],
                force_refresh: bool = False) -> tuple[object, str]:
    """Return (data, status) where status is 'hit' or 'miss'.

    - 'hit'  -> served from a fresh cache file (no network).
    - 'miss' -> fetched fresh via fetch_fn() and written to the cache.
    """
    CACHE_DIR.mkdir(exist_ok=True)
    path = CACHE_DIR / f"{key}.json"

    if not force_refresh and path.exists():
        age = time.time() - path.stat().st_mtime
        if age < ttl_seconds:
            return json.loads(path.read_text(encoding="utf-8")), "hit"

    data = fetch_fn()
    path.write_text(json.dumps(data), encoding="utf-8")
    return data, "miss"


def clear_cache() -> int:
    """Delete all cache files. Returns the number removed."""
    if not CACHE_DIR.exists():
        return 0
    files = list(CACHE_DIR.glob("*.json"))
    for f in files:
        f.unlink()
    return len(files)
