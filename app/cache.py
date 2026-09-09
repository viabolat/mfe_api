from __future__ import annotations

import time
from typing import Any


class TTLCache:
    """Simple in-process TTL cache.

    Keeps repeat requests off mfe.gov.ro's server. Not shared across
    serverless instances, but Vercel's Fluid Compute reuses warm
    instances so this still absorbs bursty traffic in practice.
    """

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.monotonic() + self._ttl, value)
