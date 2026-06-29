"""
Example: Using AuroraClient to store scraped sports data.

Demonstrates:
- Database connection pooling
- Inserting match data
- Upserting (insert or update) data
- Batch inserts for performance
- Querying matches
- Proper connection cleanup
"""

import asyncio
import os

from sipap_batch_scraper.storage.aurora import AuroraClient


async def main() -> None:
    """Demonstrate Aurora client usage."""
    print("=== AuroraClient Example ===\n")

    # Initialize client with connection details
    # In production, these would come from environment variables or AWS Secrets Manager
    client = AuroraClient(
        host=os.getenv('AURORA_HOST', 'localhost'),
        port=int(os.getenv('AURORA_PORT', '5432')),
        database=os.getenv('AURORA_DATABASE', 'sipap_dev'),
        user=os.getenv('AURORA_USER', 'sipap_admin'),
        password=os.getenv('AURORA_PASSWORD', 'password'),
        min_pool_size=5,
        max_pool_size=20
    )

    try:
        # Connect to database (creates connection pool)
        print("1. Connecting to Aurora database...")
        await client.connect()
        print("   ✓ Connection pool created\n")

        # Example 1: Insert match data
        print("2. Inserting match data...")
        match_data = {
            'external_id': 'flash_12345',
            'home_team': 'Arsenal',
            'away_team': 'Chelsea',
            'scheduled_at': '2026-06-27T15:00:00Z',
            'league': 'Premier League',
            'source': 'flashscore'
        }
        await client.insert_match(match_data)
        print(f"   ✓ Inserted: {match_data['home_team']} vs {match_data['away_team']}\n")

        # Example 2: Upsert match data (insert or update)
        print("3. Upserting match data (update existing)...")
        match_data['status'] = 'live'
        await client.upsert_match(match_data)
        print(f"   ✓ Updated status to 'live'\n")

        # Example 3: Batch insert multiple matches
        print("4. Batch inserting multiple matches...")
        matches = [
            {
                'external_id': 'flash_12346',
                'home_team': 'Liverpool',
                'away_team': 'Manchester City',
                'scheduled_at': '2026-06-27T17:30:00Z',
                'league': 'Premier League',
                'source': 'flashscore'
            },
            {
                'external_id': 'flash_12347',
                'home_team': 'Real Madrid',
                'away_team': 'Barcelona',
                'scheduled_at': '2026-06-27T20:00:00Z',
                'league': 'La Liga',
                'source': 'flashscore'
            }
        ]
        await client.batch_insert_matches(matches)
        print(f"   ✓ Batch inserted {len(matches)} matches\n")

        # Example 4: Query matches
        print("5. Querying matches...")
        results = await client.query_matches(
            date='2026-06-27',
            league='Premier League',
            limit=10
        )
        print(f"   ✓ Found {len(results)} Premier League matches on 2026-06-27")
        for match in results:
            print(f"      - {match['home_team']} vs {match['away_team']}")
        print()

        # Example 5: Insert team stats
        print("6. Inserting team statistics...")
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
        await client.insert_team_stats(team_stats)
        print(f"   ✓ Inserted stats for {team_stats['team_id']}\n")

    except Exception as e:
        print(f"   ✗ Error: {e}\n")

    finally:
        # Always close connection pool
        print("7. Closing connection pool...")
        await client.close()
        print("   ✓ Connection pool closed\n")

    print("=== Example Complete ===")


if __name__ == '__main__':
    # Note: Requires Aurora PostgreSQL database running
    # Set environment variables: AURORA_HOST, AURORA_PORT, etc.
    # Or use Docker: docker-compose up postgres
    asyncio.run(main())
