"""
FlashScore scraper example.

Demonstrates scraping match schedules and live scores from FlashScore.

Usage:
    python examples/example_flashscore_scraper.py

Requirements:
    - Internet connection
    - Playwright browsers installed (run: playwright install chromium)
"""

import asyncio
import json
from datetime import UTC, datetime

from sipap_batch_scraper.scrapers.flashscore import FlashScoreScraper


async def main() -> None:
    """Demonstrate FlashScore scraper capabilities."""
    print("=" * 70)
    print("FlashScore Scraper Example")
    print("=" * 70)
    print()

    # Initialize scraper
    scraper = FlashScoreScraper(timeout=30000)  # 30 second timeout
    print(f"✓ Initialized FlashScore scraper")
    print(f"  Base URL: {scraper.base_url}")
    print(f"  Timeout: {scraper.timeout}ms")
    print()

    # Example 1: Scrape today's matches
    print("-" * 70)
    print("Example 1: Scraping Today's Matches")
    print("-" * 70)
    try:
        matches = await scraper.scrape_today_matches()

        print(f"✓ Found {len(matches)} matches today")
        print()

        # Display first 3 matches
        for i, match in enumerate(matches[:3], 1):
            print(f"Match {i}:")
            print(f"  Home: {match.get('home_team')}")
            print(f"  Away: {match.get('away_team')}")
            print(f"  Time: {match.get('time')}")
            print(f"  League: {match.get('league')}")
            print(f"  Status: {match.get('status')}")
            if match.get('score'):
                print(f"  Score: {match.get('score')}")
            print()

    except Exception as e:
        print(f"✗ Error scraping today's matches: {e}")
        print()

    # Example 2: Scrape matches for specific date
    print("-" * 70)
    print("Example 2: Scraping Matches for Specific Date")
    print("-" * 70)
    target_date = "2026-06-28"  # Tomorrow
    try:
        matches = await scraper.scrape_matches(date=target_date)

        print(f"✓ Found {len(matches)} matches on {target_date}")
        print()

        # Display first match
        if matches:
            match = matches[0]
            print(f"First match on {target_date}:")
            print(f"  {match.get('home_team')} vs {match.get('away_team')}")
            print(f"  Kick-off: {match.get('time')}")
            print(f"  Competition: {match.get('league')}")
            print()

    except Exception as e:
        print(f"✗ Error scraping matches for {target_date}: {e}")
        print()

    # Example 3: Data structure inspection
    print("-" * 70)
    print("Example 3: Match Data Structure")
    print("-" * 70)
    try:
        matches = await scraper.scrape_today_matches()

        if matches:
            match = matches[0]
            print("Sample match data structure:")
            print(json.dumps(match, indent=2, default=str))
            print()

            # Field explanations
            print("Field explanations:")
            print("  home_team: Name of home team")
            print("  away_team: Name of away team")
            print("  time: Match time or minute if live (e.g., '15:00' or '67'')")
            print("  league: Competition name (e.g., 'Premier League')")
            print("  status: 'scheduled', 'live', or 'finished'")
            print("  score: Match score (only for live/finished matches)")
            print("  external_id: FlashScore match ID")
            print("  source: Always 'flashscore'")
            print("  scraped_at: ISO 8601 timestamp when data was scraped")
            print()

    except Exception as e:
        print(f"✗ Error: {e}")
        print()

    # Example 4: Filtering matches
    print("-" * 70)
    print("Example 4: Filtering Matches")
    print("-" * 70)
    try:
        all_matches = await scraper.scrape_today_matches()

        # Filter live matches
        live_matches = [m for m in all_matches if m.get('status') == 'live']
        print(f"✓ Found {len(live_matches)} live matches")

        # Filter by league
        premier_league = [m for m in all_matches if 'Premier League' in m.get('league', '')]
        print(f"✓ Found {len(premier_league)} Premier League matches")

        # Filter scheduled matches
        scheduled = [m for m in all_matches if m.get('status') == 'scheduled']
        print(f"✓ Found {len(scheduled)} scheduled matches")
        print()

    except Exception as e:
        print(f"✗ Error: {e}")
        print()

    # Example 5: Integration with storage
    print("-" * 70)
    print("Example 5: Storage Integration (Simulation)")
    print("-" * 70)
    print("In production, scraped data would be:")
    print("  1. Stored in Aurora PostgreSQL (match schedule)")
    print("  2. Cached in Redis (30-minute TTL)")
    print("  3. Exposed via sipap-sports-data-mcp tools")
    print()
    print("Example workflow:")
    print("  matches = await scraper.scrape_today_matches()")
    print("  for match in matches:")
    print("      await aurora_client.upsert_match({")
    print("          'external_id': match['external_id'],")
    print("          'home_team': match['home_team'],")
    print("          'away_team': match['away_team'],")
    print("          'scheduled_at': match['time'],")
    print("          'league': match['league'],")
    print("          'source': 'flashscore',")
    print("      })")
    print("      await redis_client.setex(")
    print("          f\"match:{match['external_id']}\",")
    print("          1800,  # 30 minutes")
    print("          match")
    print("      )")
    print()

    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print("✓ FlashScore scraper successfully demonstrated")
    print(f"✓ All examples completed at {datetime.now(UTC).isoformat()}")
    print()
    print("Features demonstrated:")
    print("  • Scraping today's matches")
    print("  • Scraping matches for specific date")
    print("  • Parsing match data with BeautifulSoup")
    print("  • Handling live vs scheduled matches")
    print("  • Extracting scores, times, teams, leagues")
    print("  • Anti-detection via BaseScraper (Playwright + stealth)")
    print("  • Structured data output ready for storage")
    print()
    print("Next steps:")
    print("  • Build Futbol24 scraper (similar structure)")
    print("  • Build ESPN scraper (fallback source)")
    print("  • Create daily harvest job (orchestrate all scrapers)")
    print("  • Deploy to AWS Fargate + EventBridge scheduler")
    print()


if __name__ == "__main__":
    asyncio.run(main())
