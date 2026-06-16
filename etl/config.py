"""Runtime configuration for the ETL pipeline.

Reads from environment variables so the same code runs locally (SQLite) and in
production (Neon Postgres) with no code changes — only ``DATABASE_URL`` differs.
"""

import os
from pathlib import Path

# Project paths.
ETL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ETL_DIR.parent
SCHEMA_PATH = ETL_DIR / "schema.sql"

# Where to write generated PDFs by default.
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "etl_output"

# Database connection.
#   - Local / zero-setup default: a SQLite file inside the etl/ folder.
#   - Production: set DATABASE_URL to a Neon Postgres URL, e.g.
#       postgresql+psycopg2://USER:PASSWORD@HOST/DB?sslmode=require
#     (also reads NETLIFY_DATABASE_URL / NEON_DATABASE_URL as fallbacks).
def database_url() -> str:
    return (
        os.environ.get("DATABASE_URL")
        or os.environ.get("NETLIFY_DATABASE_URL")
        or os.environ.get("NEON_DATABASE_URL")
        or f"sqlite:///{(ETL_DIR / 'warehouse.db').as_posix()}"
    )


# CMS API.
CMS_BASE = "https://data.cms.gov/provider-data/api/1/datastore/query"
CMS_TIMEOUT_SECONDS = int(os.environ.get("CMS_TIMEOUT_SECONDS", "30"))
CMS_ROW_LIMIT = 500

# Caching: the state/national averages dataset changes rarely, so cache it.
# Default TTL: 24 hours (in seconds).
AVERAGES_CACHE_TTL = int(os.environ.get("AVERAGES_CACHE_TTL", str(24 * 60 * 60)))
