from __future__ import annotations

import time
from collections import OrderedDict
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class TTLInMemoryCache(Generic[T]):
    """
    Small in-memory TTL cache.

    - Uses monotonic time for TTL expiry.
    - Keeps most recently accessed items via LRU eviction.
    """

    def __init__(self, *, max_entries: int = 1024):
        self._max_entries = max_entries
        self._data: OrderedDict[str, tuple[float, T]] = OrderedDict()

    def get(self, key: str) -> Optional[T]:
        item = self._data.get(key)
        if not item:
            return None

        expires_at, value = item
        if expires_at <= time.monotonic():
            # Expired: remove and behave like a miss.
            try:
                del self._data[key]
            except KeyError:
                pass
            return None

        # LRU touch.
        self._data.move_to_end(key)
        return value

    def set(self, key: str, value: T, *, ttl_seconds: float) -> None:
        expires_at = time.monotonic() + ttl_seconds

        # Replace existing and refresh LRU position.
        if key in self._data:
            try:
                del self._data[key]
            except KeyError:
                pass

        self._data[key] = (expires_at, value)
        self._data.move_to_end(key)

        # Evict least recently used items if needed.
        while len(self._data) > self._max_entries:
            self._data.popitem(last=False)

