"""
Tests for fixture updater job.

Tests the hourly fixture refresh Lambda that updates match fixtures
and league standings from Football-Data.org and TheSportsDB.
"""

from unittest.mock import AsyncMock, patch

import pytest

from sipap_batch_scraper.jobs.fixture_updater import FixtureUpdaterJob


class TestFixtureUpdaterJob:
    """Test fixture updater job."""

    @pytest.mark.asyncio
    async def test_initialization(self) -> None:
        """Test job initialization."""
        job = FixtureUpdaterJob(
            football_data_key='test_fd_key',
            thesportsdb_key='test_tdb_key',
            aurora_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password',
            },
            redis_url='redis://localhost:6379',
        )

        assert job.football_data_key == 'test_fd_key'
        assert job.thesportsdb_key == 'test_tdb_key'

    @pytest.mark.asyncio
    async def test_fetch_fixtures_from_apis(self) -> None:
        """Test fetching fixtures from both APIs."""
        job = FixtureUpdaterJob(
            football_data_key='test_fd_key',
            thesportsdb_key='test_tdb_key',
            aurora_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password',
            },
            redis_url='redis://localhost:6379',
        )

        # Mock Football-Data.org API
        mock_fd_api = AsyncMock()
        mock_fd_api.get_matches = AsyncMock(return_value=[
            {
                'id': 12345,
                'homeTeam': {'name': 'Arsenal'},
                'awayTeam': {'name': 'Chelsea'},
                'utcDate': '2026-06-30T15:00:00Z',
                'competition': {'name': 'Premier League'},
            }
        ])

        # Mock TheSportsDB API
        mock_tdb_api = AsyncMock()
        mock_tdb_api.get_events_next_league = AsyncMock(return_value=[
            {
                'idEvent': '67890',
                'strHomeTeam': 'Arsenal',
                'strAwayTeam': 'Chelsea',
                'dateEvent': '2026-06-30',
                'strTime': '15:00:00',
            }
        ])

        job._fd_api = mock_fd_api
        job._tdb_api = mock_tdb_api

        fixtures = await job._fetch_fixtures()

        # Verify both APIs were called
        assert mock_fd_api.get_matches.call_count >= 1
        assert mock_tdb_api.get_events_next_league.call_count >= 1
        assert len(fixtures) >= 1

    @pytest.mark.asyncio
    async def test_fetch_standings(self) -> None:
        """Test fetching league standings."""
        job = FixtureUpdaterJob(
            football_data_key='test_fd_key',
            thesportsdb_key='test_tdb_key',
            aurora_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password',
            },
            redis_url='redis://localhost:6379',
        )

        # Mock Football-Data.org API
        mock_fd_api = AsyncMock()
        mock_fd_api.get_standings = AsyncMock(return_value={
            'competition': {'name': 'Premier League'},
            'standings': [
                {
                    'type': 'TOTAL',
                    'table': [
                        {
                            'position': 1,
                            'team': {'name': 'Arsenal'},
                            'points': 90,
                            'wins': 28,
                            'draws': 6,
                            'losses': 4,
                        }
                    ]
                }
            ]
        })

        job._fd_api = mock_fd_api

        standings = await job._fetch_standings()

        # Verify API was called for all 13 competitions
        assert mock_fd_api.get_standings.call_count == 13
        assert len(standings) >= 1

    @pytest.mark.asyncio
    async def test_update_fixtures_in_aurora(self) -> None:
        """Test updating fixtures in Aurora database."""
        job = FixtureUpdaterJob(
            football_data_key='test_fd_key',
            thesportsdb_key='test_tdb_key',
            aurora_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password',
            },
            redis_url='redis://localhost:6379',
        )

        fixture_data = [
            {
                'id': '12345',
                'home_team': 'Arsenal',
                'away_team': 'Chelsea',
                'date': '2026-06-30',
                'time': '15:00:00',
            }
        ]

        # Mock Aurora client
        mock_aurora = AsyncMock()
        mock_aurora.update_fixtures = AsyncMock()

        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.batch_set = AsyncMock()

        job._aurora_client = mock_aurora
        job._redis_client = mock_redis

        await job._update_fixtures(fixture_data)

        # Verify Aurora update was called
        mock_aurora.update_fixtures.assert_called()

    @pytest.mark.asyncio
    async def test_refresh_fixtures_cache(self) -> None:
        """Test refreshing fixtures cache in Redis."""
        job = FixtureUpdaterJob(
            football_data_key='test_fd_key',
            thesportsdb_key='test_tdb_key',
            aurora_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password',
            },
            redis_url='redis://localhost:6379',
        )

        fixture_data = [
            {
                'id': '12345',
                'home_team': 'Arsenal',
                'away_team': 'Chelsea',
            }
        ]

        # Mock Aurora client
        mock_aurora = AsyncMock()
        mock_aurora.update_fixtures = AsyncMock()

        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.batch_set = AsyncMock()

        job._aurora_client = mock_aurora
        job._redis_client = mock_redis

        await job._update_fixtures(fixture_data)

        # Verify Redis cache was refreshed with 6-hour TTL
        mock_redis.batch_set.assert_called_once()
        call_args = mock_redis.batch_set.call_args
        assert call_args[1]['ttl'] == 21600  # 6 hours

    @pytest.mark.asyncio
    async def test_run_success(self) -> None:
        """Test successful fixture updater execution."""
        job = FixtureUpdaterJob(
            football_data_key='test_fd_key',
            thesportsdb_key='test_tdb_key',
            aurora_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password',
            },
            redis_url='redis://localhost:6379',
        )

        # Mock all methods
        job._initialize_clients = AsyncMock()
        job._fetch_fixtures = AsyncMock(return_value=[
            {
                'id': '12345',
                'home_team': 'Arsenal',
                'away_team': 'Chelsea',
            }
        ])
        job._fetch_standings = AsyncMock(return_value=[
            {
                'league': 'Premier League',
                'team': 'Arsenal',
                'position': 1,
            }
        ])
        job._update_fixtures = AsyncMock()
        job._update_standings = AsyncMock()
        job._log_metrics = AsyncMock()
        job._cleanup_clients = AsyncMock()

        result = await job.run()

        assert result['status'] == 'success'
        assert result['fixtures_updated'] == 1
        assert result['standings_updated'] == 1
        assert 'duration_ms' in result

    @pytest.mark.asyncio
    async def test_run_handles_api_error(self) -> None:
        """Test handling of API errors during fixture update."""
        job = FixtureUpdaterJob(
            football_data_key='test_fd_key',
            thesportsdb_key='test_tdb_key',
            aurora_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password',
            },
            redis_url='redis://localhost:6379',
        )

        # Mock API failure
        job._initialize_clients = AsyncMock()
        job._fetch_fixtures = AsyncMock(side_effect=Exception('API rate limit exceeded'))
        job._cleanup_clients = AsyncMock()

        result = await job.run()

        assert result['status'] == 'error'
        assert 'API rate limit exceeded' in result['error']

    def test_lambda_handler(self) -> None:
        """Test Lambda handler function with Secrets Manager integration."""
        from sipap_batch_scraper.jobs.fixture_updater import lambda_handler

        # Mock environment variables
        with patch('os.getenv') as mock_getenv:
            mock_getenv.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'dev',
                'REDIS_URL': 'redis://localhost:6379',
            }.get(key, default)

            # Mock get_secret() to return API keys and DB credentials
            with patch('sipap_batch_scraper.jobs.fixture_updater.get_secret') as mock_get_secret:
                def get_secret_side_effect(secret_name: str) -> dict:
                    if secret_name == 'sipap/dev/api-keys':
                        return {
                            'FOOTBALL_DATA_KEY': 'test_fd_key',
                            'THESPORTSDB_KEY': 'test_tdb_key',
                        }
                    elif secret_name == 'sipap/dev/aurora-credentials':
                        return {
                            'host': 'localhost',
                            'port': '5432',
                            'database': 'test_db',
                            'username': 'test_user',
                            'password': 'test_pass',
                        }
                    return {}

                mock_get_secret.side_effect = get_secret_side_effect

                # Mock asyncio.run to return the result directly
                with patch('asyncio.run') as mock_run:
                    mock_run.return_value = {
                        'status': 'success',
                        'fixtures_updated': 15,
                        'standings_updated': 5,
                        'duration_ms': 2000,
                    }

                    # Call Lambda handler
                    event = {}
                    context = {}
                    result = lambda_handler(event, context)

                    # Verify result
                    assert result['statusCode'] == 200
                    assert 'success' in result['body']

                    # Verify get_secret was called twice (once for API keys, once for DB creds)
                    assert mock_get_secret.call_count == 2
