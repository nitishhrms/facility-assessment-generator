"""Medelite facility-report ETL package.

A small but real data pipeline that:
  1. EXTRACTS facility data from the public CMS Provider Data Catalog API,
  2. TRANSFORMS it into one normalized report model (+ QA verdicts & data quality),
  3. LOADS dated snapshots into a SQL warehouse (SQLite locally, Neon Postgres in prod),
  4. and can render an executive-ready PDF from the same model.

This mirrors the JavaScript app's pure transform core in Python so the same
business logic backs both the live UI and the automated/batch pipeline.
"""

__version__ = "0.1.0"
