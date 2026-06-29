"""
Example usage of FixtureUpdaterJob.

This example demonstrates how to use the hourly fixture updater job
to refresh match fixtures and league standings from Football-Data.org
and TheSportsDB.
"""

import asyncio
import os

from sipap_batch_scraper.jobs import FixtureUpdaterJob


async def main() -> None:
    """Run fixture updater job example."""
    # Configure job
    job = FixtureUpdaterJob(
        football_data_key=os.getenv('FOOTBALL_DATA_KEY', 'your_fd_api_key_here'),
        thesportsdb_key=os.getenv('THESPORTSDB_KEY', '123'),
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
    print("Starting fixture updater job...")
    result = await job.run()

    # Display results
    print(f"\nJob Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Fixtures Updated: {result['fixtures_updated']}")
        print(f"Standings Updated: {result['standings_updated']}")
        print(f"Duration: {result['duration_ms']}ms")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
        print(f"Duration: {result['duration_ms']}ms")


if __name__ == '__main__':
    asyncio.run(main())
