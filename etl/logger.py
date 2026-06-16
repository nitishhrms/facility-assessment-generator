"""Structured (JSON) logging.

Each pipeline event is written as one JSON line to a dated log file under
``etl/.logs/``. JSON lines are machine-queryable (grep/jq, or load into a table),
which is what you want for an auditable data pipeline — unlike loose print()s.
The human-friendly console summary stays in the CLI; this is the durable record.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from etl.config import ETL_DIR

LOG_DIR = ETL_DIR / ".logs"


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if fields:
            payload.update(fields)
        return json.dumps(payload)


def get_logger(name: str = "etl") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:  # already configured
        return logger
    logger.setLevel(logging.INFO)
    LOG_DIR.mkdir(exist_ok=True)
    handler = logging.FileHandler(
        LOG_DIR / f"pipeline-{datetime.now().date().isoformat()}.log", encoding="utf-8"
    )
    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, **fields) -> None:
    """Emit one structured event, e.g. log_event(log, 'facility_processed', ccn=..., status=...)."""
    logger.info(event, extra={"fields": fields})
