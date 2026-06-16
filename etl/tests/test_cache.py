"""Tests for the TTL cache (no network — uses a counting fake fetcher)."""

import etl.cache as cache_mod
from etl.cache import cached_json


def _redirect_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path / ".cache")


def test_miss_then_hit(tmp_path, monkeypatch):
    _redirect_cache(tmp_path, monkeypatch)
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return {"value": calls["n"]}

    data1, status1 = cached_json("k", ttl_seconds=3600, fetch_fn=fetch)
    data2, status2 = cached_json("k", ttl_seconds=3600, fetch_fn=fetch)

    assert status1 == "miss"
    assert status2 == "hit"
    assert data1 == data2 == {"value": 1}
    assert calls["n"] == 1  # fetched only once


def test_expired_ttl_refetches(tmp_path, monkeypatch):
    _redirect_cache(tmp_path, monkeypatch)
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return calls["n"]

    cached_json("k", ttl_seconds=0, fetch_fn=fetch)          # writes
    _, status = cached_json("k", ttl_seconds=0, fetch_fn=fetch)  # ttl 0 -> stale
    assert status == "miss"
    assert calls["n"] == 2


def test_force_refresh(tmp_path, monkeypatch):
    _redirect_cache(tmp_path, monkeypatch)
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return calls["n"]

    cached_json("k", ttl_seconds=3600, fetch_fn=fetch)
    _, status = cached_json("k", ttl_seconds=3600, fetch_fn=fetch, force_refresh=True)
    assert status == "miss"
    assert calls["n"] == 2
