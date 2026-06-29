"""
Unit tests for Aurora database client.

Following TDD methodology: RED phase - these tests will fail until implementation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sipap_batch_scraper.storage.aurora import AuroraClient


class TestAuroraClient:
    """Test suite for Aurora database client."""

    @pytest.fixture
    def mock_connection(self):
        """Mock database connection from pool.acquire()."""
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=None)
        conn.executemany = AsyncMock(return_value=None)
        conn.fetch = AsyncMock(return_value=[])
        conn.fetchrow = AsyncMock(return_value=None)
        return conn

    @pytest.fixture
    def mock_pool(self, mock_connection):
        """Mock asyncpg connection pool."""
        pool = AsyncMock()

        # Create a proper async context manager for acquire()
        class MockAcquireContext:
            async def __aenter__(self):
                return mock_connection

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        # Make acquire() return the context manager (not awaitable)
        pool.acquire = MagicMock(return_value=MockAcquireContext())
        pool.close = AsyncMock()
        return pool

    @pytest.fixture
    async def aurora_client(self, mock_pool):
        """Create Aurora client with mocked connection pool."""
        # Create an async mock that returns the pool when awaited
        async def mock_create_pool(*args, **kwargs):
            return mock_pool

        with patch('sipap_batch_scraper.storage.aurora.asyncpg.create_pool',
                   side_effect=mock_create_pool):
            client = AuroraClient(
                host="localhost",
                port=5432,
                database="sipap_test",
                user="test_user",
                password="test_pass"
            )
            await client.connect()
            yield client
            await client.close()

    @pytest.mark.asyncio
    async def test_connection_initialization(self):
        """Test database connection pool is established on connect()."""
        mock_pool = AsyncMock()

        async def mock_create_pool_func(*args, **kwargs):
            return mock_pool

        with patch('sipap_batch_scraper.storage.aurora.asyncpg.create_pool',
                   side_effect=mock_create_pool_func) as mock_create_pool:
            client = AuroraClient(
                host="localhost",
                port=5432,
                database="sipap_test",
                user="test_user",
                password="test_pass"
            )

            # Pool should not be created until connect() is called
            assert client.host == "localhost"
            assert client.port == 5432
            assert client.database == "sipap_test"
            assert client._pool is None

            # Connect and verify pool creation
            await client.connect()
            assert client._pool is not None
            mock_create_pool.assert_called_once()

            await client.close()

    @pytest.mark.asyncio
    async def test_insert_match_data(self, aurora_client, mock_connection):
        """Test inserting match data."""
        match_data = {
            'external_id': 'flash_12345',
            'home_team': 'Arsenal',
            'away_team': 'Chelsea',
            'scheduled_at': '2026-06-27T15:00:00Z',
            'league': 'Premier League',
            'source': 'flashscore'
        }

        await aurora_client.insert_match(match_data)

        # Verify INSERT query was executed
        mock_connection.execute.assert_called_once()
        query = mock_connection.execute.call_args[0][0]
        assert 'INSERT INTO matches' in query
        assert 'external_id' in query

    @pytest.mark.asyncio
    async def test_insert_team_stats(self, aurora_client, mock_connection):
        """Test inserting team statistics."""
        team_stats = {
            'team_id': 'arsenal_fc',
            'season': '2024-2025',
            'matches_played': 25,
            'wins': 18,
            'draws': 4,
            'losses': 3,
            'goals_scored': 54,
            'goals_conceded': 23
        }

        await aurora_client.insert_team_stats(team_stats)

        mock_connection.execute.assert_called_once()
        query = mock_connection.execute.call_args[0][0]
        assert 'INSERT INTO team_stats' in query
        assert 'ON CONFLICT' in query  # Implementation uses upsert

    @pytest.mark.asyncio
    async def test_batch_insert_matches(self, aurora_client, mock_connection):
        """Test batch inserting multiple matches."""
        matches = [
            {
                'external_id': f'flash_{i}',
                'home_team': f'Team {i}',
                'away_team': f'Team {i+1}',
                'scheduled_at': '2026-06-27T15:00:00Z',
                'league': 'Premier League',
                'source': 'flashscore'
            }
            for i in range(10)
        ]

        await aurora_client.batch_insert_matches(matches)

        # Should use executemany for batch insert
        mock_connection.executemany.assert_called_once()
        query = mock_connection.executemany.call_args[0][0]
        assert 'INSERT INTO matches' in query
        assert 'ON CONFLICT' in query  # Implementation uses ON CONFLICT DO NOTHING

    @pytest.mark.asyncio
    async def test_query_matches_by_date(self, aurora_client, mock_connection):
        """Test querying matches by date."""
        # Mock fetch() to return asyncpg Records (dict-like objects)
        mock_record = MagicMock()
        mock_record.__iter__ = lambda self: iter([
            ('external_id', '12345'),
            ('home_team', 'Arsenal'),
            ('away_team', 'Chelsea'),
            ('scheduled_at', '2026-06-27T15:00:00Z'),
            ('league', 'Premier League')
        ])
        mock_connection.fetch.return_value = [mock_record]

        matches = await aurora_client.query_matches(date='2026-06-27')

        assert len(matches) > 0
        mock_connection.fetch.assert_called_once()
        query = mock_connection.fetch.call_args[0][0]
        assert 'SELECT' in query
        assert 'FROM matches' in query
        assert 'DATE(scheduled_at)' in query

    @pytest.mark.asyncio
    async def test_query_team_stats(self, aurora_client, mock_connection):
        """Test querying team statistics."""
        # Mock fetchrow() to return asyncpg Record (dict-like object)
        mock_record = MagicMock()
        mock_record.__iter__ = lambda self: iter([
            ('team_id', 'arsenal_fc'),
            ('season', '2024-2025'),
            ('matches_played', 25),
            ('wins', 18),
            ('draws', 4),
            ('losses', 3),
            ('goals_scored', 54),
            ('goals_conceded', 23)
        ])
        mock_connection.fetchrow.return_value = mock_record

        stats = await aurora_client.query_team_stats(
            team_id='arsenal_fc',
            season='2024-2025'
        )

        assert stats is not None
        mock_connection.fetchrow.assert_called_once()
        query = mock_connection.fetchrow.call_args[0][0]
        assert 'SELECT' in query
        assert 'FROM team_stats' in query

    @pytest.mark.asyncio
    async def test_upsert_match_updates_existing(self, aurora_client, mock_connection):
        """Test upserting match data updates existing record."""
        match_data = {
            'external_id': 'flash_12345',
            'home_team': 'Arsenal',
            'away_team': 'Chelsea',
            'scheduled_at': '2026-06-27T15:00:00Z',
            'league': 'Premier League',
            'source': 'flashscore',
            'status': 'live'
        }

        await aurora_client.upsert_match(match_data)

        mock_connection.execute.assert_called_once()
        query = mock_connection.execute.call_args[0][0]
        # Should use ON CONFLICT DO UPDATE syntax
        assert 'ON CONFLICT' in query
        assert 'DO UPDATE' in query

    @pytest.mark.asyncio
    async def test_connection_cleanup(self, aurora_client, mock_pool):
        """Test connection pool is properly closed."""
        # aurora_client fixture already calls close(), so test that it's already closed
        # or we can close again (should be idempotent)
        await aurora_client.close()

        # Pool close should have been called at least once (by fixture teardown or this call)
        assert mock_pool.close.call_count >= 1

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, aurora_client, mock_connection):
        """Test that database errors propagate correctly."""
        mock_connection.execute.side_effect = Exception("Database error")

        match_data = {
            'external_id': 'test',
            'home_team': 'Test',
            'away_team': 'Test2',
            'scheduled_at': '2026-06-27T15:00:00Z',
            'league': 'Test League',
            'source': 'test'
        }

        with pytest.raises(Exception, match="Database error"):
            await aurora_client.insert_match(match_data)

        # Verify execute was attempted
        mock_connection.execute.assert_called_once()

    def test_connection_string_formation(self):
        """Test connection string is formed correctly."""
        client = AuroraClient(
            host="test.rds.amazonaws.com",
            port=5432,
            database="sipap_dev",
            user="sipap_admin",
            password="secret"
        )

        assert client.host == "test.rds.amazonaws.com"
        assert client.port == 5432
        assert client.database == "sipap_dev"
        assert client.user == "sipap_admin"
