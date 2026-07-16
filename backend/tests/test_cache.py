"""The in-memory cache honors read/write and TTL expiry."""

import time

from voidfall.app.cache import InMemoryCache


def test_set_and_get():
    cache = InMemoryCache()
    cache.set("k", "v", ttl_seconds=60)
    assert cache.get("k") == "v"


def test_missing_key_returns_none():
    assert InMemoryCache().get("absent") is None


def test_invalidate_removes_entry():
    cache = InMemoryCache()
    cache.set("k", "v")
    cache.invalidate("k")
    assert cache.get("k") is None


def test_ttl_expiry():
    cache = InMemoryCache()
    cache.set("k", "v", ttl_seconds=0)
    time.sleep(0.01)
    assert cache.get("k") is None
