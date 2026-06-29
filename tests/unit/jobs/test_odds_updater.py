"""
Tests for odds updater job.

Tests the 30-minute odds refresh Lambda that updates betting odds
from The Odds API.
"""

from unittest.mock import AsyncMock, patch

import pytest

from sipap_batch_scraper.jobs.odds_updater import OddsUpdaterJob


class TestOddsUpdaterJob:
    """Test odds updater job."""

    @pytest.mark.asyncio
    async def test_initialization(self) -> None:
        """Test job initialization."""
        job = OddsUpdaterJob(
            odds_api_key='test_odds_key',
            aurora_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password',
            },
            redis_url='redis://localhost:6379',
        )

        assert job.odds_api_key == 'test_odds_key'

    @pytest.mark.asyncio
    async def test_fetch_odds_from_api(self) -> None:
        """Test fetching odds from The Odds API."""
        job = OddsUpdaterJob(
            odds_api_key='test_odds_key',
            aurora_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password',
            },
            redis_url='redis://localhost:6379',
        )

        # Mock API client
        mock_odds_api = AsyncMock()
        mock_odds_api.get_odds = AsyncMock(return_value=[
            {
                'id': 'odds_12345',
                'home_team': 'Arsenal',
                'away_team': 'Chelsea',
                'commence_time': '2026-06-30T15:00:00Z',
                'bookmakers': [
                    {
                        'key': 'bet365',
                        'markets': [
                            {
                                'key': 'h2h',
                                'outcomes': [
                                    {'name': 'Arsenal', 'price': 1.5},
                                    {'name': 'Chelsea', 'price': 3.0},
                                ]
                            }
                        ]
                    }
                ],
                'best_odds': {'home': 1.5, 'draw': 4.0, 'away': 3.0},
            }
        ])

        job._odds_api = mock_odds_api

        odds = await job._fetch_odds()

        # Verify API was called for all 9 soccer leagues
        assert mock_odds_api.get_odds.call_count == 9
        assert len(odds) >= 1

    @pytest.mark.asyncio
    async def test_update_odds_in_aurora(self) -> None:
        """Test updating odds in Aurora database."""
        job = OddsUpdaterJob(
            odds_api_key='test_odds_key',
            aurora_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password',
            },
            redis_url='redis://localhost:6379',
        )

        odds_data = [
            {
                'id': 'odds_12345',
                'home_team': 'Arsenal',
                'away_team': 'Chelsea',
                'bookmakers': [],
                'best_odds': {'home': 1.5, 'draw': 4.0, 'away': 3.0},
            }
        ]

        # Mock Aurora client
        mock_aurora = AsyncMock()
        mock_aurora.update_match_odds = AsyncMock()

        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.batch_set = AsyncMock()

        job._aurora_client = mock_aurora
        job._redis_client = mock_redis

        await job._update_odds(odds_data)

        # Verify Aurora update was called
        mock_aurora.update_match_odds.assert_called()

    @pytest.mark.asyncio
    async def test_refresh_redis_cache(self) -> None:
        """Test refreshing Redis cache with updated odds."""
        job = OddsUpdaterJob(
            odds_api_key='test_odds_key',
            aurora_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password',
            },
            redis_url='redis://localhost:6379',
        )

        odds_data = [
            {
                'id': 'odds_12345',
                'home_team': 'Arsenal',
                'away_team': 'Chelsea',
                'best_odds': {'home': 1.5, 'draw': 4.0, 'away': 3.0},
            }
        ]

        # Mock Aurora client
        mock_aurora = AsyncMock()
        mock_aurora.update_match_odds = AsyncMock()

        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.batch_set = AsyncMock()

        job._aurora_client = mock_aurora
        job._redis_client = mock_redis

        await job._update_odds(odds_data)

        # Verify Redis cache was refreshed with 24-hour TTL
        mock_redis.batch_set.assert_called_once()
        call_args = mock_redis.batch_set.call_args
        assert call_args[1]['ttl'] == 86400  # 24 hours

    @pytest.mark.asyncio
    async def test_run_success(self) -> None:
        """Test successful odds updater execution."""
        job = OddsUpdaterJob(
            odds_api_key='test_odds_key',
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
        job._fetch_odds = AsyncMock(return_value=[
            {
                'id': 'odds_12345',
                'home_team': 'Arsenal',
                'away_team': 'Chelsea',
                'best_odds': {'home': 1.5, 'draw': 4.0, 'away': 3.0},
            }
        ])
        job._update_odds = AsyncMock()
        job._log_metrics = AsyncMock()
        job._cleanup_clients = AsyncMock()

        result = await job.run()

        assert result['status'] == 'success'
        assert result['odds_updated'] == 1
        assert 'duration_ms' in result

    @pytest.mark.asyncio
    async def test_run_handles_api_error(self) -> None:
        """Test handling of API errors during odds update."""
        job = OddsUpdaterJob(
            odds_api_key='test_odds_key',
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
        job._fetch_odds = AsyncMock(side_effect=Exception('API rate limit exceeded'))
        job._cleanup_clients = AsyncMock()

        result = await job.run()

        assert result['status'] == 'error'
        assert 'API rate limit exceeded' in result['error']

    def test_lambda_handler(self) -> None:
        """Test Lambda handler function with Secrets Manager integration."""
        from sipap_batch_scraper.jobs.odds_updater import lambda_handler

        # Mock environment variables
        with patch('os.getenv') as mock_getenv:
            mock_getenv.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'dev',
                'REDIS_URL': 'redis://localhost:6379',
            }.get(key, default)

            # Mock get_secret() to return API keys and DB credentials
            with patch('sipap_batch_scraper.jobs.odds_updater.get_secret') as mock_get_secret:
                def get_secret_side_effect(secret_name: str) -> dict:
                    if secret_name == 'sipap/dev/api-keys':
                        return {
                            'ODDS_API_KEY': 'test_key',
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
                        'odds_updated': 10,
                        'duration_ms': 1500,
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
