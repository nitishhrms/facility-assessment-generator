"""EXTRACT layer — pulls rows from the public CMS Provider Data Catalog API.

Mirrors the JS serverless proxy: a filtered, server-side datastore query per
dataset. No CORS concerns here because this is a server-side Python process.
"""

from typing import Optional
from urllib.parse import urlencode

import requests

from etl.config import CMS_BASE, CMS_ROW_LIMIT, CMS_TIMEOUT_SECONDS
from etl.field_map import DATASETS


def _params(ccn: Optional[str] = None) -> dict[str, str]:
    params: dict[str, str] = {"limit": str(CMS_ROW_LIMIT)}
    if ccn:
        # CMS datastore filter syntax: conditions[i][property|operator|value].
        params["conditions[0][property]"] = "cms_certification_number_ccn"
        params["conditions[0][operator]"] = "="
        params["conditions[0][value]"] = ccn
    return params


def query_url(dataset: str, ccn: Optional[str] = None) -> str:
    """The exact CMS API URL a query hits — recorded for data lineage."""
    return f"{CMS_BASE}/{DATASETS[dataset]}/0?{urlencode(_params(ccn))}"


def _query(dataset: str, ccn: Optional[str] = None) -> list[dict]:
    """Run one datastore query and return its ``results`` rows."""
    resp = requests.get(
        f"{CMS_BASE}/{DATASETS[dataset]}/0", params=_params(ccn), timeout=CMS_TIMEOUT_SECONDS
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def fetch_provider(ccn: str) -> Optional[dict]:
    """One facility row, or None if the CCN matched nothing."""
    rows = _query("provider", ccn)
    return rows[0] if rows else None


def fetch_claims(ccn: str) -> list[dict]:
    """Up to 4 claims-measure rows for the facility."""
    return _query("claims", ccn)


def fetch_averages() -> list[dict]:
    """All state/nation average rows (~54). Fetched ONCE per run and reused."""
    return _query("averages")
