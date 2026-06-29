"""
Odds updater job - refreshes betting odds daily.

This Lambda function:
1. Fetches latest odds from The Odds API (9 soccer leagues)
2. Updates odds in Aurora PostgreSQL
3. Refreshes Redis cache (24-hour TTL)
4. Logs metrics to CloudWatch

Schedule: Daily at 9:00 AM UTC (via EventBridge)
Duration: ~2 minutes
Cost: ~$0.01/month (Lambda)
API Usage: 9 requests/day = 270 credits/month (54% of free tier)
"""

import asyncio
import json
import os
from datetime import UTC, datetime
from typing import Any

from sipap_batch_scraper.apis import SPORT_KEYS, OddsAPI
from sipap_batch_scraper.storage import AuroraClient, RedisClient
from sipap_batch_scraper.util import get_secret


class OddsUpdaterJob:
    """
    Daily odds updater job.

    Responsibilities:
    1. Fetch latest odds from The Odds API (9 soccer leagues)
    2. Update odds in Aurora database
    3. Refresh Redis cache (24-hour TTL)
    4. Log metrics

    Coverage:
    - Premier League, Champions League, La Liga, Bundesliga
    - Serie A, Ligue 1, Europa League
    - World Cup, European Championship (when active)

    Usage:
        job = OddsUpdaterJob(
            odds_api_key="xxx",
            aurora_config={...},
            redis_url="redis://..."
        )
        result = await job.run()
    """

    def __init__(
        self,
        odds_api_key: str,
        aurora_config: dict[str, Any],
        redis_url: str,
    ) -> None:
        """
        Initialize odds updater job.

        Args:
            odds_api_key: The Odds API key
            aurora_config: Aurora database configuration
            redis_url: Redis connection URL
        """
        self.odds_api_key = odds_api_key
        self.aurora_config = aurora_config
        self.redis_url = redis_url

        # Initialize clients (will be created in run())
        self._odds_api: OddsAPI | None = None
        self._aurora_client: AuroraClient | None = None
        self._redis_client: RedisClient | None = None

    async def _initialize_clients(self) -> None:
        """Initialize API and storage clients."""
        self._odds_api = OddsAPI(api_key=self.odds_api_key)

        # Initialize storage clients
        self._aurora_client = AuroraClient(**self.aurora_config)
        await self._aurora_client.connect()

        # Initialize Redis client
        # Parse redis_url (format: redis://hostname:6379)
        from urllib.parse import urlparse
        parsed = urlparse(self.redis_url)
        self._redis_client = RedisClient(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 6379,
            db=0
        )
        await self._redis_client.connect()

    async def _cleanup_clients(self) -> None:
        """Cleanup all clients."""
        if self._odds_api:
            await self._odds_api.close()
        if self._aurora_client:
            await self._aurora_client.close()
        if self._redis_client:
            await self._redis_client.close()

    async def _fetch_odds(self) -> list[dict[str, Any]]:
        """
        Fetch latest odds from The Odds API.

        Fetches odds for 9 soccer leagues:
        - Premier League, Champions League, La Liga, Bundesliga
        - Serie A, Ligue 1, Europa League
        - World Cup, European Championship (when active)

        Returns:
            List of odds data for upcoming matches across all leagues
        """
        assert self._odds_api is not None

        # All 9 soccer leagues supported by The Odds API free tier
        leagues = [
            SPORT_KEYS['PREMIER_LEAGUE'],
            SPORT_KEYS['CHAMPIONS_LEAGUE'],
            SPORT_KEYS['LA_LIGA'],
            SPORT_KEYS['BUNDESLIGA'],
            SPORT_KEYS['SERIE_A'],
            SPORT_KEYS['LIGUE_1'],
            SPORT_KEYS['EUROPA_LEAGUE'],
            SPORT_KEYS['WORLD_CUP'],
            SPORT_KEYS['EUROS'],
        ]

        # Create parallel tasks for all leagues
        tasks = [
            self._odds_api.get_odds(sport=league)
            for league in leagues
        ]

        # Execute all 9 leagues in parallel (graceful degradation if any fail)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Extract successful results
        all_odds: list[dict[str, Any]] = []
        for result in results:
            if not isinstance(result, Exception):
                all_odds.extend(result)  # type: ignore[arg-type]

        return all_odds

    async def _update_odds(self, odds_data: list[dict[str, Any]]) -> None:
        """
        Update odds in Aurora and Redis.

        Args:
            odds_data: List of odds data from API
        """
        assert self._aurora_client is not None
        assert self._redis_client is not None

        # Update Aurora database (odds only, not full fixture)
        for odds in odds_data:
            # Extract match identifier
            home_team = odds.get('home_team', '')
            away_team = odds.get('away_team', '')
            bookmakers = odds.get('bookmakers', [])
            best_odds = odds.get('best_odds', {})

            if not home_team or not away_team:
                continue

            # Update odds in database
            # Note: This would call a method like update_match_odds()
            # For now, simplified implementation
            await self._aurora_client.update_match_odds(  # type: ignore[attr-defined]
                home_team=home_team,
                away_team=away_team,
                bookmakers=bookmakers,
                best_odds=best_odds,
            )

        # Refresh Redis cache (24-hour TTL for daily refresh)
        cache_data = {
            f"odds:{odds.get('id', '')}": odds
            for odds in odds_data
            if odds.get('id')
        }

        if cache_data:
            await self._redis_client.batch_set(cache_data, ttl=86400)  # 24 hours

    async def _log_metrics(self, metrics: dict[str, Any]) -> None:
        """
        Log metrics to CloudWatch.

        Args:
            metrics: Metrics dictionary
        """
        # TODO: Implement CloudWatch metrics logging
        print(f"Odds Updater Metrics: {metrics}")

    async def run(self) -> dict[str, Any]:
        """
        Run odds updater job.

        Returns:
            Job result with status, odds_updated, duration_ms
        """
        start_time = datetime.now(UTC)

        try:
            # Initialize clients
            await self._initialize_clients()

            # Fetch latest odds
            odds_data = await self._fetch_odds()

            # Update Aurora + Redis
            await self._update_odds(odds_data)

            # Calculate duration
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

            # Log metrics
            metrics = {
                'odds_updated': len(odds_data),
                'duration_ms': duration_ms,
            }
            await self._log_metrics(metrics)

            return {
                'status': 'success',
                'odds_updated': len(odds_data),
                'duration_ms': duration_ms,
            }

        except Exception as e:
            import traceback
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"ERROR in odds_updater: {error_msg}")
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


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    AWS Lambda handler for odds updater.

    Fetches API keys from AWS Secrets Manager for security.

    Args:
        event: Lambda event (EventBridge scheduled event)
        context: Lambda context

    Returns:
        Lambda response with statusCode and body
    """
    # Get environment
    env = os.getenv('ENVIRONMENT', 'dev')

    # Fetch API keys from Secrets Manager
    api_keys = get_secret(f'sipap/{env}/api-keys')
    odds_api_key = api_keys['ODDS_API_KEY']

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

    # Run odds updater job
    job = OddsUpdaterJob(
        odds_api_key=odds_api_key,
        aurora_config=aurora_config,
        redis_url=redis_url,
    )

    # Execute async job
    result = asyncio.run(job.run())

    # Return Lambda response
    return {
        'statusCode': 200 if result['status'] == 'success' else 500,
        'body': json.dumps(result),
    }


if __name__ == '__main__':
    # For local testing
    asyncio.run(OddsUpdaterJob(
        odds_api_key=os.getenv('ODDS_API_KEY', ''),
        aurora_config={
            'host': os.getenv('AURORA_HOST', 'localhost'),
            'port': int(os.getenv('AURORA_PORT', '5432')),
            'database': os.getenv('AURORA_DATABASE', 'sipap_dev'),
            'user': os.getenv('AURORA_USER', 'sipap_admin'),
            'password': os.getenv('AURORA_PASSWORD', ''),
        },
        redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    ).run())
