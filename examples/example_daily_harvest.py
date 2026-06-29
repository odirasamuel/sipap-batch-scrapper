"""
Example: Daily Harvest Job

Demonstrates how to run the daily fixture harvest job that orchestrates
all 3 API clients (Football-Data.org, The Odds API, TheSportsDB).

This job:
1. Fetches fixtures from Football-Data.org (next 7 days)
2. Fetches odds from The Odds API (Premier League, Champions League)
3. Fetches events from TheSportsDB (next 15 events per league)
4. Merges and deduplicates fixtures by (home_team, away_team, date)
5. Stores in Aurora PostgreSQL + caches in Redis (6-hour TTL)

Requirements:
- API keys for Football-Data.org and The Odds API
- Aurora PostgreSQL database configured and running
- Redis cache configured and running
- Environment variables set (see below)

Usage:
    python examples/example_daily_harvest.py
"""

import asyncio
import os
from datetime import datetime

from sipap_batch_scraper.jobs import DailyHarvestJob


async def main() -> None:
    """Run daily harvest job example."""

    # Load configuration from environment variables
    fd_api_key = os.getenv('FOOTBALL_DATA_KEY', '')
    odds_api_key = os.getenv('ODDS_API_KEY', '')
    tdb_api_key = os.getenv('THESPORTSDB_KEY', '123')  # Free tier key

    # Aurora configuration
    aurora_config = {
        'host': os.getenv('AURORA_HOST', 'localhost'),
        'port': int(os.getenv('AURORA_PORT', '5432')),
        'database': os.getenv('AURORA_DATABASE', 'sipap_dev'),
        'user': os.getenv('AURORA_USER', 'sipap_admin'),
        'password': os.getenv('AURORA_PASSWORD', ''),
    }

    # Redis configuration
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

    # Validate configuration
    if not fd_api_key:
        print("❌ Error: FOOTBALL_DATA_KEY environment variable not set")
        print("   Get your free API key from: https://www.football-data.org/")
        return

    if not odds_api_key:
        print("❌ Error: ODDS_API_KEY environment variable not set")
        print("   Get your free API key from: https://the-odds-api.com/")
        return

    if not aurora_config['password']:
        print("❌ Error: AURORA_PASSWORD environment variable not set")
        return

    print("✅ Configuration loaded")
    print(f"   - Football-Data.org API key: {fd_api_key[:10]}...")
    print(f"   - The Odds API key: {odds_api_key[:10]}...")
    print(f"   - TheSportsDB API key: {tdb_api_key}")
    print(f"   - Aurora host: {aurora_config['host']}")
    print(f"   - Redis URL: {redis_url}")
    print()

    # Create daily harvest job
    job = DailyHarvestJob(
        fd_api_key=fd_api_key,
        odds_api_key=odds_api_key,
        tdb_api_key=tdb_api_key,
        aurora_config=aurora_config,
        redis_url=redis_url,
    )

    print(f"🚀 Starting daily harvest job at {datetime.now().isoformat()}")
    print()

    # Run harvest job
    result = await job.run()

    print()
    print("=" * 60)
    print("📊 Daily Harvest Job Result")
    print("=" * 60)
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"✅ Fixtures fetched: {result['fixtures_fetched']}")
        print(f"⏱️  Duration: {result['duration_ms']}ms")
        print()
        print("Next steps:")
        print("  1. Query Aurora to see stored fixtures")
        print("  2. Check Redis cache for cached fixtures")
        print("  3. Deploy to Fargate for automated daily runs")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown error')}")
        print(f"⏱️  Duration: {result['duration_ms']}ms")

    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
