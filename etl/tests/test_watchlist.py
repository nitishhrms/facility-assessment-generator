"""Watchlist tests (temp SQLite — no network)."""

import tempfile
from pathlib import Path

from etl.warehouse import (
    add_to_watchlist,
    get_engine,
    get_watchlist,
    init_schema,
    remove_from_watchlist,
)


def _fresh_engine():
    tmp = Path(tempfile.mkdtemp()) / "wl.db"
    engine = get_engine(f"sqlite:///{tmp.as_posix()}")
    init_schema(engine)
    return engine


def test_add_list_remove():
    engine = _fresh_engine()
    assert add_to_watchlist(engine, "686123", "Kendall Lakes") is True
    assert add_to_watchlist(engine, "686123") is False  # duplicate ignored
    assert add_to_watchlist(engine, "015009") is True

    wl = get_watchlist(engine)
    assert [w["ccn"] for w in wl] == ["686123", "015009"]

    remove_from_watchlist(engine, "686123")
    wl = get_watchlist(engine)
    assert [w["ccn"] for w in wl] == ["015009"]
