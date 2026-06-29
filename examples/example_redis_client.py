"""
Example: Using RedisClient to cache scraped sports data.

Demonstrates:
- Connecting to Redis (ElastiCache compatible)
- Setting cache keys with TTL
- Getting cached data
- JSON serialization/deserialization
- Batch operations
- Key pattern searching
- Proper connection cleanup
"""

import asyncio
import os

from sipap_batch_scraper.storage.redis import RedisClient


async def main() -> None:
    """Demonstrate Redis client usage."""
    print("=== RedisClient Example ===\n")

    # Initialize client with connection details
    # In production, these would come from environment variables
    client = RedisClient(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        db=0,
        decode_responses=True
    )

    try:
        # Connect to Redis
        print("1. Connecting to Redis...")
        await client.connect()
        print("   ✓ Connected to Redis\n")

        # Example 1: Set cache key with TTL
        print("2. Setting cache key with 30-minute TTL...")
        match_data = {
            'match_id': 'flash_12345',
            'home_team': 'Arsenal',
            'away_team': 'Chelsea',
            'score': '2-1',
            'status': 'live'
        }
        await client.setex('match:12345', 1800, match_data)  # 30 minutes
        print(f"   ✓ Cached: {match_data['home_team']} vs {match_data['away_team']}\n")

        # Example 2: Get cached data
        print("3. Retrieving cached match data...")
        cached_match = await client.get('match:12345')
        print(f"   ✓ Retrieved: {cached_match}\n")

        # Example 3: Batch set multiple keys
        print("4. Batch setting multiple match keys...")
        matches = {
            'match:12346': {'home': 'Liverpool', 'away': 'Man City', 'score': '3-2'},
            'match:12347': {'home': 'Real Madrid', 'away': 'Barcelona', 'score': '1-1'},
            'match:12348': {'home': 'Bayern', 'away': 'Dortmund', 'score': '4-0'}
        }
        await client.batch_set(matches, ttl=1800)
        print(f"   ✓ Batch set {len(matches)} matches\n")

        # Example 4: Batch get multiple keys
        print("5. Batch retrieving multiple matches...")
        keys = ['match:12346', 'match:12347', 'match:12348']
        results = await client.batch_get(keys)
        print(f"   ✓ Retrieved {len(results)} matches:")
        for i, result in enumerate(results):
            if result:
                print(f"      - {keys[i]}: {result}")
        print()

        # Example 5: Search for keys by pattern
        print("6. Searching for keys by pattern...")
        all_match_keys = await client.keys('match:*')
        print(f"   ✓ Found {len(all_match_keys)} match keys:")
        for key in all_match_keys:
            print(f"      - {key}")
        print()

        # Example 7: Delete cache key
        print("7. Deleting cache key...")
        await client.delete('match:12345')
        exists = await client.exists('match:12345')
        print(f"   ✓ Key deleted, exists: {exists}\n")

        # Example 8: Increment counter
        print("8. Incrementing scrape counter...")
        await client.increment('scrape_counter', 1)
        await client.increment('scrape_counter', 5)
        counter_value = await client.get('scrape_counter')
        print(f"   ✓ Scrape counter: {counter_value}\n")

        # Example 9: Set expiry on existing key
        print("9. Setting expiry on counter...")
        await client.expire('scrape_counter', 60)  # 60 seconds
        print(f"   ✓ Counter will expire in 60 seconds\n")

    except Exception as e:
        print(f"   ✗ Error: {e}\n")

    finally:
        # Always close connection
        print("10. Closing Redis connection...")
        await client.close()
        print("    ✓ Connection closed\n")

    print("=== Example Complete ===")


if __name__ == '__main__':
    # Note: Requires Redis server running
    # Set environment variables: REDIS_HOST, REDIS_PORT
    # Or use Docker: docker-compose up redis
    asyncio.run(main())
