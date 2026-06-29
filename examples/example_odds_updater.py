"""
Example usage of OddsUpdaterJob.

This example demonstrates how to use the 30-minute odds updater job
to refresh betting odds from The Odds API and update Aurora + Redis.
"""

import asyncio
import os

from sipap_batch_scraper.jobs import OddsUpdaterJob


async def main() -> None:
    """Run odds updater job example."""
    # Configure job
    job = OddsUpdaterJob(
        odds_api_key=os.getenv('ODDS_API_KEY', 'your_odds_api_key_here'),
        aurora_config={
            'host': os.getenv('AURORA_HOST', 'localhost'),
            'port': int(os.getenv('AURORA_PORT', '5432')),
            'database': os.getenv('AURORA_DATABASE', 'sipap_dev'),
            'user': os.getenv('AURORA_USER', 'sipap_admin'),
            'password': os.getenv('AURORA_PASSWORD', 'your_password_here'),
        },
        redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    )

    # Run the job
    print("Starting odds updater job...")
    result = await job.run()

    # Display results
    print(f"\nJob Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Odds Updated: {result['odds_updated']}")
        print(f"Duration: {result['duration_ms']}ms")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
        print(f"Duration: {result['duration_ms']}ms")


if __name__ == '__main__':
    asyncio.run(main())
