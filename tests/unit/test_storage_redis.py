"""
Unit tests for Redis cache client.

Following TDD methodology: RED phase - these tests will fail until implementation.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sipap_batch_scraper.storage.redis import RedisClient


class TestRedisClient:
    """Test suite for Redis cache client."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis connection."""
        redis = AsyncMock()
        redis.set = AsyncMock(return_value=True)
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock(return_value=True)
        redis.delete = AsyncMock(return_value=1)
        redis.exists = AsyncMock(return_value=1)
        redis.mget = AsyncMock(return_value=[])
        redis.keys = AsyncMock(return_value=[])
        redis.flushdb = AsyncMock(return_value=True)
        redis.incrby = AsyncMock(return_value=1)
        redis.expire = AsyncMock(return_value=True)
        redis.close = AsyncMock()

        # Mock pipeline for batch operations
        pipeline = AsyncMock()
        pipeline.setex = MagicMock()
        pipeline.set = MagicMock()
        pipeline.execute = AsyncMock()
        pipeline.__aenter__ = AsyncMock(return_value=pipeline)
        pipeline.__aexit__ = AsyncMock(return_value=None)
        redis.pipeline = MagicMock(return_value=pipeline)

        return redis

    @pytest.fixture
    async def redis_client(self, mock_redis):
        """Create Redis client with mocked connection."""
        async def mock_from_url(*args, **kwargs):
            return mock_redis

        with patch('sipap_batch_scraper.storage.redis.aioredis.from_url',
                   side_effect=mock_from_url):
            client = RedisClient(
                host="localhost",
                port=6379,
                db=0
            )
            await client.connect()
            yield client
            await client.close()

    @pytest.mark.asyncio
    async def test_set_cache_key(self, redis_client, mock_redis):
        """Test setting cache key."""
        data = {'team': 'Arsenal', 'stats': {'wins': 18}}

        await redis_client.set('team:arsenal', data)

        mock_redis.set.assert_called_once()
        # Should serialize dict to JSON
        call_args = mock_redis.set.call_args
        assert 'team:arsenal' in call_args[0]

    @pytest.mark.asyncio
    async def test_set_cache_with_ttl(self, redis_client, mock_redis):
        """Test setting cache key with TTL."""
        data = {'match_id': '12345'}
        ttl = 1800  # 30 minutes

        await redis_client.setex('match:12345', ttl, data)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == 'match:12345'
        assert call_args[1] == 1800

    @pytest.mark.asyncio
    async def test_get_cache_key(self, redis_client, mock_redis):
        """Test getting cache key."""
        cached_data = json.dumps({'team': 'Arsenal'})
        mock_redis.get.return_value = cached_data

        result = await redis_client.get('team:arsenal')

        assert result == {'team': 'Arsenal'}
        mock_redis.get.assert_called_once_with('team:arsenal')

    @pytest.mark.asyncio
    async def test_get_cache_miss_returns_none(self, redis_client, mock_redis):
        """Test cache miss returns None."""
        mock_redis.get.return_value = None

        result = await redis_client.get('nonexistent:key')

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_cache_key(self, redis_client, mock_redis):
        """Test deleting cache key."""
        await redis_client.delete('team:arsenal')

        mock_redis.delete.assert_called_once_with('team:arsenal')

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_existing_key(self, redis_client, mock_redis):
        """Test exists returns True for existing key."""
        mock_redis.exists.return_value = 1

        exists = await redis_client.exists('team:arsenal')

        assert exists is True
        mock_redis.exists.assert_called_once_with('team:arsenal')

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_missing_key(self, redis_client, mock_redis):
        """Test exists returns False for missing key."""
        mock_redis.exists.return_value = 0

        exists = await redis_client.exists('nonexistent:key')

        assert exists is False

    @pytest.mark.asyncio
    async def test_batch_set_multiple_keys(self, redis_client, mock_redis):
        """Test batch setting multiple keys."""
        data = {
            'match:1': {'home': 'Arsenal', 'away': 'Chelsea'},
            'match:2': {'home': 'Liverpool', 'away': 'Man Utd'}
        }

        await redis_client.batch_set(data, ttl=3600)

        # Should use pipeline and call setex for each key
        mock_redis.pipeline.assert_called_once()
        pipeline = mock_redis.pipeline.return_value
        assert pipeline.setex.call_count == 2
        pipeline.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_get_multiple_keys(self, redis_client, mock_redis):
        """Test batch getting multiple keys."""
        mock_redis.mget.return_value = [
            json.dumps({'home': 'Arsenal'}),
            json.dumps({'home': 'Liverpool'}),
            None
        ]

        keys = ['match:1', 'match:2', 'match:3']
        results = await redis_client.batch_get(keys)

        assert len(results) == 3
        assert results[0] == {'home': 'Arsenal'}
        assert results[1] == {'home': 'Liverpool'}
        assert results[2] is None

    @pytest.mark.asyncio
    async def test_cache_key_pattern_search(self, redis_client, mock_redis):
        """Test searching for keys by pattern."""
        mock_redis.keys.return_value = [
            'match:12345',
            'match:12346',
            'match:12347'
        ]

        keys = await redis_client.keys('match:*')

        assert len(keys) == 3
        assert 'match:12345' in keys
        mock_redis.keys.assert_called_once_with('match:*')

    @pytest.mark.asyncio
    async def test_flush_all_keys(self, redis_client, mock_redis):
        """Test flushing all keys in database."""
        await redis_client.flushdb()

        mock_redis.flushdb.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_counter(self, redis_client, mock_redis):
        """Test incrementing counter."""
        mock_redis.incrby.return_value = 5

        count = await redis_client.incr('scraper:count')

        assert count == 5
        mock_redis.incrby.assert_called_once_with('scraper:count', 1)

    @pytest.mark.asyncio
    async def test_connection_cleanup(self, redis_client, mock_redis):
        """Test Redis connection is properly closed."""
        # redis_client fixture already calls close(), so test that it's already closed
        # or we can close again (should be idempotent)
        await redis_client.close()

        # Close should have been called at least once (by fixture teardown or this call)
        assert mock_redis.close.call_count >= 1

    @pytest.mark.asyncio
    async def test_json_serialization_error_handling(self, redis_client, mock_redis):
        """Test handling of non-JSON-serializable data."""
        from datetime import datetime

        # datetime objects are not JSON serializable by default
        data = {'timestamp': datetime.now()}

        with pytest.raises(TypeError):
            await redis_client.set('test:key', data)

    def test_connection_url_formation(self):
        """Test Redis connection URL is formed correctly."""
        client = RedisClient(
            host="cache.redis.amazonaws.com",
            port=6379,
            db=0,
            password="secret"
        )

        assert client.host == "cache.redis.amazonaws.com"
        assert client.port == 6379
        assert client.db == 0
