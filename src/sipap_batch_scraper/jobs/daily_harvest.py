"""
Daily harvest job - orchestrates fixture collection from Football-Data.org and TheSportsDB.

This job:
1. Fetches fixtures from Football-Data.org (next 7 days, 13 competitions)
2. Fetches events from TheSportsDB (9 soccer leagues for metadata enrichment)
3. Merges fixtures by (home_team, away_team, date) to deduplicate
4. Stores in Aurora PostgreSQL + caches in Redis (6-hour TTL)

Note: Odds are fetched separately by odds_updater.py (daily at 9 AM UTC)

Coverage: 9 soccer leagues (EPL, UCL, La Liga, Bundesliga, Serie A, Ligue 1,
          Europa League, World Cup, European Championship)

Schedule: Daily at 12:00 AM UTC (via EventBridge + Fargate)
Duration: 2-3 minutes (10 parallel API calls: 1 FD + 9 TDB)
Cost: ~$0.05/month (Fargate)
"""

import asyncio
import os
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sipap_batch_scraper.apis import (
    LEAGUE_IDS,
    FootballDataAPI,
    OddsAPI,
    TheSportsDBClient,
)
from sipap_batch_scraper.storage import AuroraClient, RedisClient
from sipap_batch_scraper.util import get_secret


def normalize_team_name(team_name: str) -> str:
    """
    Normalize team name for matching across APIs.

    Args:
        team_name: Team name from API (e.g., "Arsenal FC", "Manchester United")

    Returns:
        Normalized team name (lowercase, no suffixes, no special chars)

    Examples:
        >>> normalize_team_name("Arsenal FC")
        'arsenal'
        >>> normalize_team_name("Manchester United")
        'manchester'
        >>> normalize_team_name("Brighton & Hove Albion")
        'brighton hove albion'
    """
    # Convert to lowercase
    name = team_name.lower().strip()

    # Remove common suffixes
    suffixes = [' fc', ' afc', ' united', ' city', ' cf']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]

    # Remove special characters but keep spaces
    name = re.sub(r'[^a-z0-9\s]', '', name)

    # Normalize multiple spaces to single space
    name = ' '.join(name.split())

    return name


def normalize_date(date_str: str) -> str:
    """
    Normalize date string to YYYY-MM-DD format.

    Args:
        date_str: ISO 8601 date string (e.g., "2026-06-30T15:00:00Z")

    Returns:
        Date string in YYYY-MM-DD format
    """
    # Parse ISO 8601 and extract date
    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    return dt.strftime('%Y-%m-%d')


def create_fixture_key(home_team: str, away_team: str, date: str) -> str:
    """
    Create unique fixture key for deduplication.

    Args:
        home_team: Home team name
        away_team: Away team name
        date: Match date (YYYY-MM-DD or ISO 8601)

    Returns:
        Unique fixture key (normalized)

    Example:
        >>> create_fixture_key("Arsenal", "Chelsea", "2026-06-30")
        'arsenal_chelsea_2026-06-30'
    """
    # Normalize date if ISO 8601
    if 'T' in date:
        date = normalize_date(date)

    # Create key with normalized team names
    return f"{normalize_team_name(home_team)}_{normalize_team_name(away_team)}_{date}"


def merge_fixtures(
    fd_fixtures: list[dict[str, Any]],
    odds_fixtures: list[dict[str, Any]],
    tdb_fixtures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Merge fixtures from multiple APIs by (home_team, away_team, date).

    Strategy:
    1. Create fixture key for each fixture
    2. Group by key
    3. Merge data from all sources for same fixture
    4. Return deduplicated list

    Args:
        fd_fixtures: Fixtures from Football-Data.org
        odds_fixtures: Fixtures with odds from The Odds API
        tdb_fixtures: Fixtures from TheSportsDB

    Returns:
        Merged and deduplicated fixture list
    """
    merged: dict[str, dict[str, Any]] = {}

    # Process Football-Data.org fixtures (PRIMARY source)
    for fixture in fd_fixtures:
        home = fixture.get('homeTeam', {}).get('name', '')
        away = fixture.get('awayTeam', {}).get('name', '')
        date = fixture.get('utcDate', '')

        if not home or not away or not date:
            continue

        key = create_fixture_key(home, away, date)

        merged[key] = {
            'id': fixture.get('id', ''),
            'home_team': home,
            'away_team': away,
            'scheduled_at': date,
            'league': fixture.get('competition', {}).get('name', ''),
            'source': 'football-data.org',
            'status': fixture.get('status', 'SCHEDULED'),
            'venue': fixture.get('venue', ''),
            'score': fixture.get('score', {}),
        }

    # Enrich with odds from The Odds API
    for fixture in odds_fixtures:
        home = fixture.get('home_team', '')
        away = fixture.get('away_team', '')
        date = fixture.get('commence_time', '')

        if not home or not away or not date:
            continue

        key = create_fixture_key(home, away, date)

        if key in merged:
            # Enrich existing fixture with odds
            merged[key]['odds'] = fixture.get('bookmakers', [])
            merged[key]['best_odds'] = fixture.get('best_odds', {})
        else:
            # Create new fixture from odds data
            merged[key] = {
                'id': fixture.get('id', ''),
                'home_team': home,
                'away_team': away,
                'scheduled_at': date,
                'league': fixture.get('sport_title', ''),
                'source': 'theoddsapi.com',
                'odds': fixture.get('bookmakers', []),
                'best_odds': fixture.get('best_odds', {}),
            }

    # Enrich with metadata from TheSportsDB
    for fixture in tdb_fixtures:
        home = fixture.get('strHomeTeam', '')
        away = fixture.get('strAwayTeam', '')
        date = fixture.get('dateEvent', '')

        if not home or not away or not date:
            continue

        # TheSportsDB uses YYYY-MM-DD format, convert to ISO 8601
        time = fixture.get('strTime', '00:00:00')
        date_time = f"{date}T{time}Z"

        key = create_fixture_key(home, away, date)

        if key in merged:
            # Enrich existing fixture with metadata
            merged[key]['team_badges'] = {
                'home': fixture.get('strHomeTeamBadge', ''),
                'away': fixture.get('strAwayTeamBadge', ''),
            }
            merged[key]['venue'] = fixture.get('strVenue', merged[key].get('venue', ''))
        else:
            # Create new fixture from TheSportsDB data
            merged[key] = {
                'id': fixture.get('idEvent', ''),
                'home_team': home,
                'away_team': away,
                'scheduled_at': date_time,
                'league': fixture.get('strLeague', ''),
                'source': 'thesportsdb.com',
                'team_badges': {
                    'home': fixture.get('strHomeTeamBadge', ''),
                    'away': fixture.get('strAwayTeamBadge', ''),
                },
                'venue': fixture.get('strVenue', ''),
            }

    return list(merged.values())


class DailyHarvestJob:
    """
    Daily harvest job - orchestrates fixture collection from all APIs.

    Responsibilities:
    1. Fetch fixtures from Football-Data.org (next 7 days)
    2. Fetch odds from The Odds API (Premier League, Champions League)
    3. Fetch events from TheSportsDB (next 15 events per league)
    4. Merge and deduplicate fixtures
    5. Store in Aurora + cache in Redis (6-hour TTL)
    6. Log metrics to CloudWatch

    Usage:
        job = DailyHarvestJob(
            fd_api_key="xxx",
            odds_api_key="yyy",
            tdb_api_key="123",
            aurora_config={...},
            redis_url="redis://..."
        )
        result = await job.run()
    """

    def __init__(
        self,
        fd_api_key: str,
        odds_api_key: str,
        tdb_api_key: str,
        aurora_config: dict[str, Any],
        redis_url: str,
    ) -> None:
        """
        Initialize daily harvest job.

        Args:
            fd_api_key: Football-Data.org API key
            odds_api_key: The Odds API key
            tdb_api_key: TheSportsDB API key (usually "123" for free tier)
            aurora_config: Aurora database configuration
            redis_url: Redis connection URL
        """
        self.fd_api_key = fd_api_key
        self.odds_api_key = odds_api_key
        self.tdb_api_key = tdb_api_key
        self.aurora_config = aurora_config
        self.redis_url = redis_url

        # Initialize clients (will be created in run())
        self._fd_api: FootballDataAPI | None = None
        self._odds_api: OddsAPI | None = None
        self._tdb_api: TheSportsDBClient | None = None
        self._aurora_client: AuroraClient | None = None
        self._redis_client: RedisClient | None = None

    async def _initialize_clients(self) -> None:
        """Initialize all API and storage clients."""
        self._fd_api = FootballDataAPI(api_key=self.fd_api_key)
        self._odds_api = OddsAPI(api_key=self.odds_api_key)
        self._tdb_api = TheSportsDBClient(api_key=self.tdb_api_key)

        # Initialize storage clients
        self._aurora_client = AuroraClient(**self.aurora_config)
        await self._aurora_client.connect()

        # Redis client from URL
        # Note: Simplified initialization, actual implementation would parse URL
        # For now, assume redis_url contains necessary connection info

    async def _cleanup_clients(self) -> None:
        """Cleanup all API and storage clients."""
        if self._fd_api:
            await self._fd_api.close()
        if self._odds_api:
            await self._odds_api.close()
        if self._tdb_api:
            await self._tdb_api.close()
        if self._aurora_client:
            await self._aurora_client.close()
        if self._redis_client:
            pass  # Redis client cleanup if needed

    async def _fetch_fixtures(self) -> list[dict[str, Any]]:
        """
        Fetch fixtures from all 3 APIs in parallel.

        Returns:
            Merged and deduplicated fixture list
        """
        assert self._fd_api is not None
        assert self._odds_api is not None
        assert self._tdb_api is not None

        # Calculate date range (next 7 days)
        today = datetime.now(UTC)
        next_week = today + timedelta(days=7)
        date_from = today.strftime('%Y-%m-%d')
        date_to = next_week.strftime('%Y-%m-%d')

        # Fetch from Football-Data.org and TheSportsDB in parallel
        # Note: Odds are fetched separately by odds_updater.py (daily at 11 PM)
        fd_task = self._fd_api.get_matches(date_from=date_from, date_to=date_to)

        # Fetch events from TheSportsDB for all 9 soccer leagues
        thesportsdb_leagues = [
            LEAGUE_IDS['PREMIER_LEAGUE'],
            LEAGUE_IDS['CHAMPIONS_LEAGUE'],
            LEAGUE_IDS['LA_LIGA'],
            LEAGUE_IDS['BUNDESLIGA'],
            LEAGUE_IDS['SERIE_A'],
            LEAGUE_IDS['LIGUE_1'],
            LEAGUE_IDS['EUROPA_LEAGUE'],
            LEAGUE_IDS['WORLD_CUP'],
            LEAGUE_IDS['EUROS'],
        ]

        tdb_tasks = [
            self._tdb_api.get_events_next_league(league_id)
            for league_id in thesportsdb_leagues
        ]

        # Execute all requests in parallel (1 FD + 9 TDB = 10 total)
        results = await asyncio.gather(
            fd_task,
            *tdb_tasks,
            return_exceptions=True
        )

        # Extract results (handle exceptions with proper type guards)
        # Structure: [FD] + [9 TDB] = 10 total results
        # Note: Odds are NOT fetched here (handled by odds_updater.py)

        # 1. Football-Data.org fixtures (result[0])
        fd_fixtures: list[dict[str, Any]]
        if isinstance(results[0], Exception):
            fd_fixtures = []
        else:
            fd_fixtures = results[0]  # type: ignore[assignment]

        # 2. TheSportsDB results (results[1:10] - 9 leagues)
        tdb_flat: list[dict[str, Any]] = []
        for result in results[1:]:
            if not isinstance(result, Exception):
                tdb_flat.extend(result)  # type: ignore[arg-type]

        # No odds data in daily harvest (handled by odds_updater.py daily at 11 PM)
        all_odds: list[dict[str, Any]] = []

        # Merge fixtures
        merged = merge_fixtures(fd_fixtures, all_odds, tdb_flat)

        return merged

    async def _store_fixtures(self, fixtures: list[dict[str, Any]]) -> None:
        """
        Store fixtures in Aurora and Redis.

        Args:
            fixtures: List of merged fixtures
        """
        assert self._aurora_client is not None
        assert self._redis_client is not None

        # Store in Aurora (batch insert)
        if fixtures:
            await self._aurora_client.batch_insert_matches(fixtures)

        # Store in Redis (6-hour TTL)
        cache_data = {
            f"fixture:{fixture['id']}": fixture
            for fixture in fixtures
            if fixture.get('id')
        }

        if cache_data:
            await self._redis_client.batch_set(cache_data, ttl=21600)  # 6 hours

    async def _log_metrics(self, metrics: dict[str, Any]) -> None:
        """
        Log metrics to CloudWatch.

        Args:
            metrics: Metrics dictionary with:
                - fixtures_fetched: Number of fixtures fetched
                - duration_ms: Job duration in milliseconds
                - api_success_rate: API success rate
        """
        # TODO: Implement CloudWatch metrics logging
        # For now, just print metrics
        print(f"Daily Harvest Metrics: {metrics}")

    async def run(self) -> dict[str, Any]:
        """
        Run daily harvest job.

        Returns:
            Job result with:
                - status: 'success' or 'error'
                - fixtures_fetched: Number of fixtures fetched
                - duration_ms: Job duration in milliseconds
                - error: Error message (if status='error')
        """
        start_time = datetime.now(UTC)

        try:
            # Initialize clients
            await self._initialize_clients()

            # Fetch fixtures from all APIs
            fixtures = await self._fetch_fixtures()

            # Store in Aurora + Redis
            await self._store_fixtures(fixtures)

            # Calculate duration
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

            # Log metrics
            metrics = {
                'fixtures_fetched': len(fixtures),
                'duration_ms': duration_ms,
                'api_success_rate': 1.0,  # TODO: Calculate actual success rate
            }
            await self._log_metrics(metrics)

            return {
                'status': 'success',
                'fixtures_fetched': len(fixtures),
                'duration_ms': duration_ms,
            }

        except Exception as e:
            import traceback
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"ERROR in daily_harvest: {error_msg}")
            print(f"Traceback: {traceback.format_exc()}")
            return {
                'status': 'error',
                'error': error_msg,
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc(),
                'duration_ms': duration_ms,
            }

        finally:
            # Cleanup clients
            await self._cleanup_clients()


async def main() -> None:
    """
    Main entry point for daily harvest job (Fargate).

    Fetches API keys from AWS Secrets Manager for security.

    Usage:
        python -m sipap_batch_scraper.jobs.daily_harvest
    """
    # Get environment
    env = os.getenv('ENVIRONMENT', 'dev')

    # Fetch API keys from Secrets Manager
    api_keys = get_secret(f'sipap/{env}/api-keys')
    fd_api_key = api_keys['FOOTBALL_DATA_KEY']
    odds_api_key = api_keys['ODDS_API_KEY']
    tdb_api_key = api_keys.get('THESPORTSDB_KEY', '123')

    # Fetch database credentials from Secrets Manager
    db_creds = get_secret(f'sipap/{env}/aurora-credentials')

    aurora_config = {
        'host': db_creds['host'],
        'port': int(db_creds['port']),
        'database': db_creds['database'],
        'user': db_creds['username'],
        'password': db_creds['password'],
    }

    # Redis URL from environment variable (not sensitive)
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

    # Run harvest job
    job = DailyHarvestJob(
        fd_api_key=fd_api_key,
        odds_api_key=odds_api_key,
        tdb_api_key=tdb_api_key,
        aurora_config=aurora_config,
        redis_url=redis_url,
    )

    result = await job.run()

    print(f"Daily Harvest Result: {result}")


if __name__ == '__main__':
    asyncio.run(main())
