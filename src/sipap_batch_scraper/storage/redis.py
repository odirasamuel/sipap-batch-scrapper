"""
Redis cache client for batch scraper.

Handles caching of scraped sports data for fast access.
"""

import json
from typing import Any

import redis.asyncio as aioredis


class RedisClient:
    """
    Redis cache client for batch scraper.

    Features:
    - Async Redis operations
    - JSON serialization/deserialization
    - TTL support
    - Batch operations
    - Key pattern matching

    Example:
        >>> client = RedisClient(
        ...     host="sipap-dev-cache.redis.amazonaws.com",
        ...     port=6379,
        ...     db=0
        ... )
        >>> await client.connect()
        >>> await client.setex('match:12345', 1800, {'home': 'Arsenal'})
        >>> match = await client.get('match:12345')
        >>> await client.close()
    """

    def __init__(
        self,
        host: str,
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        decode_responses: bool = True
    ) -> None:
        """
        Initialize Redis client.

        Args:
            host: Redis host
            port: Redis port (default 6379)
            db: Database number (default 0)
            password: Optional password
            decode_responses: Decode byte responses to strings
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.decode_responses = decode_responses
        self._client: aioredis.Redis[Any] | None = None

    async def connect(self) -> None:
        """Create Redis connection."""
        if self._client is None:
            self._client = await aioredis.from_url(
                f"redis://{self.host}:{self.port}/{self.db}",
                password=self.password,
                decode_responses=self.decode_responses
            )

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def set(self, key: str, value: Any) -> bool:
        """
        Set cache key.

        Args:
            key: Cache key
            value: Value (will be JSON serialized if dict/list)

        Returns:
            True if successful
        """
        assert self._client is not None, "Must call connect() before set()"
        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        result = await self._client.set(key, value)
        return bool(result)

    async def setex(self, key: str, ttl: int, value: Any) -> bool:
        """
        Set cache key with TTL.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds
            value: Value (will be JSON serialized if dict/list)

        Returns:
            True if successful

        Example:
            >>> await client.setex('match:12345', 1800, {'home': 'Arsenal'})
        """
        assert self._client is not None, "Must call connect() before setex()"
        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        return await self._client.setex(key, ttl, value)

    async def get(self, key: str) -> Any | None:
        """
        Get cache key.

        Args:
            key: Cache key

        Returns:
            Cached value (JSON deserialized if possible) or None

        Example:
            >>> match = await client.get('match:12345')
            >>> # Returns: {'home': 'Arsenal', 'away': 'Chelsea'}
        """
        assert self._client is not None, "Must call connect() before get()"
        value = await self._client.get(key)

        if value is None:
            return None

        # Try to deserialize JSON
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def delete(self, *keys: str) -> int:
        """
        Delete cache keys.

        Args:
            keys: One or more cache keys

        Returns:
            Number of keys deleted

        Example:
            >>> deleted = await client.delete('match:1', 'match:2')
        """
        assert self._client is not None, "Must call connect() before delete()"
        return await self._client.delete(*keys)

    async def exists(self, key: str) -> bool:
        """
        Check if key exists.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        assert self._client is not None, "Must call connect() before exists()"
        return bool(await self._client.exists(key))

    async def batch_set(
        self,
        data: dict[str, Any],
        ttl: int | None = None
    ) -> None:
        """
        Batch set multiple keys.

        Args:
            data: Dictionary of key-value pairs
            ttl: Optional TTL for all keys

        Example:
            >>> await client.batch_set({
            ...     'match:1': {'home': 'Arsenal'},
            ...     'match:2': {'home': 'Liverpool'}
            ... }, ttl=3600)
        """
        assert self._client is not None, "Must call connect() before batch_set()"
        async with self._client.pipeline() as pipe:
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)

                if ttl:
                    pipe.setex(key, ttl, value)
                else:
                    pipe.set(key, value)

            await pipe.execute()

    async def batch_get(self, keys: list[str]) -> list[Any | None]:
        """
        Batch get multiple keys.

        Args:
            keys: List of cache keys

        Returns:
            List of values (None for missing keys)

        Example:
            >>> values = await client.batch_get(['match:1', 'match:2', 'match:3'])
            >>> # Returns: [{'home': 'Arsenal'}, {'home': 'Liverpool'}, None]
        """
        assert self._client is not None, "Must call connect() before batch_get()"
        values = await self._client.mget(keys)

        results: list[Any | None] = []
        for value in values:
            if value is None:
                results.append(None)
            else:
                try:
                    results.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    results.append(value)

        return results

    async def keys(self, pattern: str) -> list[str]:
        """
        Search for keys by pattern.

        Args:
            pattern: Key pattern (e.g., 'match:*')

        Returns:
            List of matching keys

        Example:
            >>> keys = await client.keys('match:*')
            >>> # Returns: ['match:12345', 'match:12346', ...]
        """
        assert self._client is not None, "Must call connect() before keys()"
        return await self._client.keys(pattern)

    async def flushdb(self) -> bool:
        """
        Flush all keys in current database.

        WARNING: This deletes ALL keys in the database!

        Returns:
            True if successful
        """
        assert self._client is not None, "Must call connect() before flushdb()"
        return await self._client.flushdb()

    async def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment counter.

        Args:
            key: Counter key
            amount: Increment amount (default 1)

        Returns:
            New counter value

        Example:
            >>> count = await client.incr('scraper:total_matches')
        """
        assert self._client is not None, "Must call connect() before incr()"
        return await self._client.incrby(key, amount)

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set TTL on existing key.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        assert self._client is not None, "Must call connect() before expire()"
        return await self._client.expire(key, ttl)
