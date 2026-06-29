"""
Tests for daily harvest job.

Tests the orchestration of API clients, fixture merging, and storage operations.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sipap_batch_scraper.jobs.daily_harvest import (
    DailyHarvestJob,
    merge_fixtures,
    normalize_team_name,
)


class TestNormalizeTeamName:
    """Test team name normalization for fixture merging."""

    def test_normalize_basic_name(self) -> None:
        """Test normalization of basic team name."""
        assert normalize_team_name("Arsenal FC") == "arsenal"
        assert normalize_team_name("Chelsea") == "chelsea"

    def test_normalize_removes_suffix(self) -> None:
        """Test removal of common suffixes (FC, AFC, United, City)."""
        assert normalize_team_name("Manchester United") == "manchester"
        assert normalize_team_name("Manchester City") == "manchester"
        assert normalize_team_name("Arsenal FC") == "arsenal"
        assert normalize_team_name("Liverpool AFC") == "liverpool"

    def test_normalize_handles_whitespace(self) -> None:
        """Test handling of extra whitespace."""
        assert normalize_team_name("  Arsenal  ") == "arsenal"
        assert normalize_team_name("Manchester  United") == "manchester"

    def test_normalize_handles_special_characters(self) -> None:
        """Test removal of special characters."""
        assert normalize_team_name("Inter Miami CF") == "inter miami"
        assert normalize_team_name("Brighton & Hove Albion") == "brighton hove albion"


class TestMergeFixtures:
    """Test fixture merging logic."""

    def test_merge_empty_lists(self) -> None:
        """Test merging with empty input lists."""
        result = merge_fixtures([], [], [])
        assert result == []

    def test_merge_single_source(self) -> None:
        """Test merging from single API source."""
        fd_fixtures = [
            {
                'id': 'fd_12345',
                'homeTeam': {'name': 'Arsenal'},
                'awayTeam': {'name': 'Chelsea'},
                'utcDate': '2026-06-30T15:00:00Z',
                'competition': {'name': 'Premier League'},
                'source': 'football-data.org',
            }
        ]

        result = merge_fixtures(fd_fixtures, [], [])

        assert len(result) == 1
        assert result[0]['home_team'] == 'Arsenal'
        assert result[0]['away_team'] == 'Chelsea'
        assert result[0]['source'] == 'football-data.org'

    def test_merge_deduplicates_identical_fixtures(self) -> None:
        """Test deduplication of identical fixtures from multiple sources."""
        fd_fixture = {
            'id': 'fd_12345',
            'homeTeam': {'name': 'Arsenal'},
            'awayTeam': {'name': 'Chelsea'},
            'utcDate': '2026-06-30T15:00:00Z',
            'competition': {'name': 'Premier League'},
            'source': 'football-data.org',
        }

        odds_fixture = {
            'id': 'odds_67890',
            'home_team': 'Arsenal',
            'away_team': 'Chelsea',
            'commence_time': '2026-06-30T15:00:00Z',
            'sport_title': 'Soccer - Premier League',
            'source': 'theoddsapi.com',
        }

        result = merge_fixtures([fd_fixture], [odds_fixture], [])

        # Should merge into 1 fixture with enriched data
        assert len(result) == 1
        assert result[0]['home_team'] == 'Arsenal'
        assert result[0]['away_team'] == 'Chelsea'
        assert 'odds' in result[0]  # Enriched with odds data

    def test_merge_preserves_unique_fixtures(self) -> None:
        """Test that unique fixtures from different sources are preserved."""
        fd_fixture = {
            'id': 'fd_12345',
            'homeTeam': {'name': 'Arsenal'},
            'awayTeam': {'name': 'Chelsea'},
            'utcDate': '2026-06-30T15:00:00Z',
            'competition': {'name': 'Premier League'},
            'source': 'football-data.org',
        }

        odds_fixture = {
            'id': 'odds_67890',
            'home_team': 'Liverpool',
            'away_team': 'Manchester United',
            'commence_time': '2026-06-30T17:00:00Z',
            'sport_title': 'Soccer - Premier League',
            'source': 'theoddsapi.com',
        }

        result = merge_fixtures([fd_fixture], [odds_fixture], [])

        # Should have 2 distinct fixtures
        assert len(result) == 2


class TestDailyHarvestJob:
    """Test daily harvest job orchestration."""

    @pytest.mark.asyncio
    async def test_initialization(self) -> None:
        """Test job initialization."""
        job = DailyHarvestJob(
            fd_api_key='test_fd_key',
            odds_api_key='test_odds_key',
            tdb_api_key='123',
            aurora_config={'host': 'localhost'},
            redis_url='redis://localhost:6379',
        )

        assert job.fd_api_key == 'test_fd_key'
        assert job.odds_api_key == 'test_odds_key'
        assert job.tdb_api_key == '123'

    @pytest.mark.asyncio
    async def test_fetch_fixtures_from_all_apis(self) -> None:
        """Test fetching fixtures from all 3 APIs in parallel."""
        job = DailyHarvestJob(
            fd_api_key='test_fd_key',
            odds_api_key='test_odds_key',
            tdb_api_key='123',
            aurora_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password',
            },
            redis_url='redis://localhost:6379',
        )

        # Mock API clients directly on the job instance
        mock_fd_api = AsyncMock()
        mock_fd_api.get_matches = AsyncMock(return_value=[
            {
                'id': 'fd_12345',
                'homeTeam': {'name': 'Arsenal'},
                'awayTeam': {'name': 'Chelsea'},
                'utcDate': '2026-06-30T15:00:00Z',
                'competition': {'name': 'Premier League'},
                'source': 'football-data.org',
            }
        ])

        mock_odds_api = AsyncMock()
        mock_odds_api.get_odds = AsyncMock(return_value=[])

        mock_tdb_api = AsyncMock()
        mock_tdb_api.get_events_next_league = AsyncMock(return_value=[])

        # Set mock clients directly on job instance
        job._fd_api = mock_fd_api
        job._odds_api = mock_odds_api
        job._tdb_api = mock_tdb_api

        fixtures = await job._fetch_fixtures()

        # Verify APIs were called (odds API NOT called - handled by odds_updater.py)
        mock_fd_api.get_matches.assert_called_once()
        mock_tdb_api.get_events_next_league.assert_called()
        # Note: odds_api.get_odds() is NOT called in daily_harvest (handled by odds_updater.py)

        # Verify fixtures returned
        assert len(fixtures) >= 1

    @pytest.mark.asyncio
    async def test_store_fixtures_in_aurora_and_redis(self) -> None:
        """Test storing fixtures in Aurora and Redis."""
        job = DailyHarvestJob(
            fd_api_key='test_fd_key',
            odds_api_key='test_odds_key',
            tdb_api_key='123',
            aurora_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'test_db',
                'user': 'test_user',
                'password': 'test_password',
            },
            redis_url='redis://localhost:6379',
        )

        fixtures = [
            {
                'id': 'fd_12345',
                'home_team': 'Arsenal',
                'away_team': 'Chelsea',
                'scheduled_at': '2026-06-30T15:00:00Z',
                'league': 'Premier League',
                'source': 'football-data.org',
            }
        ]

        # Mock storage clients
        mock_aurora = AsyncMock()
        mock_aurora.batch_insert_matches = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.batch_set = AsyncMock()

        with patch.object(job, '_aurora_client', mock_aurora):
            with patch.object(job, '_redis_client', mock_redis):
                await job._store_fixtures(fixtures)

        # Verify Aurora batch insert called
        mock_aurora.batch_insert_matches.assert_called_once_with(fixtures)

        # Verify Redis cache populated
        mock_redis.batch_set.assert_called_once()
        call_args = mock_redis.batch_set.call_args
        assert call_args[1]['ttl'] == 21600  # 6 hours

    @pytest.mark.asyncio
    async def test_run_success(self) -> None:
        """Test successful harvest job execution."""
        job = DailyHarvestJob(
            fd_api_key='test_fd_key',
            odds_api_key='test_odds_key',
            tdb_api_key='123',
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
                'id': 'fd_12345',
                'home_team': 'Arsenal',
                'away_team': 'Chelsea',
                'scheduled_at': '2026-06-30T15:00:00Z',
                'league': 'Premier League',
                'source': 'football-data.org',
            }
        ])
        job._store_fixtures = AsyncMock()
        job._log_metrics = AsyncMock()
        job._cleanup_clients = AsyncMock()

        result = await job.run()

        assert result['status'] == 'success'
        assert result['fixtures_fetched'] == 1
        assert 'duration_ms' in result

    @pytest.mark.asyncio
    async def test_run_handles_api_error(self) -> None:
        """Test handling of API errors during harvest."""
        job = DailyHarvestJob(
            fd_api_key='test_fd_key',
            odds_api_key='test_odds_key',
            tdb_api_key='123',
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
        job._fetch_fixtures = AsyncMock(side_effect=Exception('API timeout'))
        job._cleanup_clients = AsyncMock()

        result = await job.run()

        assert result['status'] == 'error'
        assert 'API timeout' in result['error']

    @pytest.mark.asyncio
    async def test_main_entry_point(self) -> None:
        """Test main() entry point function with Secrets Manager integration."""
        from sipap_batch_scraper.jobs.daily_harvest import main

        # Mock environment variables
        with patch('os.getenv') as mock_getenv:
            mock_getenv.side_effect = lambda key, default='': {
                'ENVIRONMENT': 'dev',
                'REDIS_URL': 'redis://localhost:6379',
            }.get(key, default)

            # Mock get_secret() to return API keys and DB credentials
            with patch('sipap_batch_scraper.jobs.daily_harvest.get_secret') as mock_get_secret:
                def get_secret_side_effect(secret_name: str) -> dict:
                    if secret_name == 'sipap/dev/api-keys':
                        return {
                            'FOOTBALL_DATA_KEY': 'test_fd_key',
                            'ODDS_API_KEY': 'test_odds_key',
                            'THESPORTSDB_KEY': '123',
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

                # Mock DailyHarvestJob.run() to avoid actual execution
                with patch('sipap_batch_scraper.jobs.daily_harvest.DailyHarvestJob.run') as mock_run:
                    mock_run.return_value = {
                        'status': 'success',
                        'fixtures_fetched': 25,
                        'duration_ms': 2500,
                    }

                    # Call main() function
                    await main()

                    # Verify get_secret was called twice (once for API keys, once for DB creds)
                    assert mock_get_secret.call_count == 2

                    # Verify job was executed
                    mock_run.assert_called_once()
