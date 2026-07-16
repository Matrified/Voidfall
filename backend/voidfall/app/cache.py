"""Caching layer.

A tiny, swappable cache abstraction. In development (and tests) an in-process store with
TTL expiry is used — zero dependencies, deterministic. In production, setting
``VOIDFALL_REDIS_URL`` transparently swaps in a Redis-backed implementation.

Consumers depend only on the :class:`Cache` protocol, never on Redis directly, which
keeps the interface layer honest and the whole thing unit-testable.
"""

from __future__ import annotations

import time
from typing import Protocol

from .config import get_settings


class Cache(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ttl_seconds: int = 300) -> None: ...
    def invalidate(self, key: str) -> None: ...


class InMemoryCache:
    """Process-local cache with per-entry expiry."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: str, ttl_seconds: int = 300) -> None:
        self._store[key] = (time.monotonic() + ttl_seconds, value)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)


class RedisCache:
    """Redis-backed cache. Imported lazily so redis is only needed in production."""

    def __init__(self, url: str) -> None:
        import redis  # local import: optional dependency

        self._client = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> str | None:
        return self._client.get(key)

    def set(self, key: str, value: str, ttl_seconds: int = 300) -> None:
        self._client.set(key, value, ex=ttl_seconds)

    def invalidate(self, key: str) -> None:
        self._client.delete(key)


_cache: Cache | None = None


def get_cache() -> Cache:
    """Return the process-wide cache, choosing Redis when configured."""
    global _cache
    if _cache is None:
        redis_url = get_settings().redis_url
        _cache = RedisCache(redis_url) if redis_url else InMemoryCache()
    return _cache
