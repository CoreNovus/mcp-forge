"""Cache provider base class for mcp-forge.

Defines the interface for key-value caching with optional TTL.
Subclass BaseCacheProvider and implement get(), put(), delete().

Similar to Django's BaseCache backend pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseCacheProvider(ABC):
    """Base class for cache backends.

    Subclass and implement the three abstract methods to integrate any
    cache system (Redis, Memcached, DynamoDB, etc.).

    Example::

        class RedisCache(BaseCacheProvider):
            async def get(self, key):
                data = await self.redis.get(key)
                return json.loads(data) if data else None

            async def put(self, key, data, ttl_seconds=None):
                await self.redis.set(key, json.dumps(data), ex=ttl_seconds)

            async def delete(self, key):
                return await self.redis.delete(key) > 0
    """

    @abstractmethod
    async def get(self, key: str) -> dict | None:
        """Retrieve a cached value by key.

        Args:
            key: The cache key.

        Returns:
            The cached dict, or None if not found or expired.
        """
        ...

    @abstractmethod
    async def put(self, key: str, data: dict, ttl_seconds: int | None = None) -> None:
        """Store a value with optional TTL.

        Args:
            key: The cache key.
            data: The dict to store.
            ttl_seconds: Optional time-to-live in seconds. None means no expiry.
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a cached value.

        Args:
            key: The cache key.

        Returns:
            True if the key existed and was deleted, False otherwise.
        """
        ...

    async def get_or_default(self, key: str, default: dict) -> dict:
        """Get a value, returning a default if not found.

        Args:
            key: The cache key.
            default: Value to return if key is not found.

        Returns:
            The cached dict or the default.
        """
        result = await self.get(key)
        return result if result is not None else default
