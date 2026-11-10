"""In-memory TTL cache with thread safety for BAKAI India MCP Server.

Prevents rate limits and reduces response latency for frequently requested
data such as news feeds, weather forecasts, and radio stream verifications.
"""

from __future__ import annotations

import asyncio
import functools
import time
from typing import Any, Callable, Dict, Optional, Tuple


class TTLCache:
    """Thread-safe and async-safe In-Memory TTL Cache."""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000) -> None:
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._lock = asyncio.Lock()

    def get_sync(self, key: str) -> Optional[Any]:
        """Synchronously retrieves value if present and not expired."""
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set_sync(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Synchronously sets value with TTL in seconds."""
        if len(self._store) >= self.max_size:
            # Purge expired or oldest items
            now = time.time()
            expired_keys = [k for k, (_, exp) in self._store.items() if now > exp]
            for k in expired_keys:
                del self._store[k]
            if len(self._store) >= self.max_size:
                # Remove first 100 items if still over size
                for k in list(self._store.keys())[:100]:
                    del self._store[k]

        expires_at = time.time() + (ttl if ttl is not None else self.default_ttl)
        self._store[key] = (value, expires_at)

    async def get(self, key: str) -> Optional[Any]:
        """Asynchronously retrieves value if present and not expired."""
        async with self._lock:
            return self.get_sync(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Asynchronously sets value with TTL in seconds."""
        async with self._lock:
            self.set_sync(key, value, ttl)

    def clear(self) -> None:
        """Clears all cached entries."""
        self._store.clear()


# Global cache instance
cache = TTLCache(default_ttl=300)


def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator for caching async function results by arguments."""

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Construct deterministic key
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            cached_val = await cache.get(cache_key)
            if cached_val is not None:
                return cached_val

            result = await func(*args, **kwargs)
            if result is not None:
                await cache.set(cache_key, result, ttl=ttl)
            return result

        return wrapper

    return decorator
