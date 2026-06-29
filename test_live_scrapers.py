#!/usr/bin/env python3
"""
Live scraper validation script.

Tests all three scrapers against real websites to validate:
1. CSS selectors are correct
2. Data extraction works as expected
3. Output format matches schema

Usage:
    python test_live_scrapers.py
"""

import asyncio
import json
from typing import Any

from sipap_batch_scraper.scrapers.flashscore import FlashScoreScraper
from sipap_batch_scraper.scrapers.futbol24 import Futbol24Scraper
from sipap_batch_scraper.scrapers.espn import ESPNScraper


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_data(label: str, data: Any, max_items: int = 3) -> None:
    """Print data in a formatted way."""
    print(f"\n{label}:")
    print("-" * 40)

    if isinstance(data, list):
        print(f"Found {len(data)} items")
        if data:
            print(f"\nShowing first {min(len(data), max_items)} items:\n")
            for i, item in enumerate(data[:max_items], 1):
                print(f"Item {i}:")
                print(json.dumps(item, indent=2, default=str))
                print()
    elif isinstance(data, dict):
        print(json.dumps(data, indent=2, default=str))
    else:
        print(data)


async def test_flashscore() -> None:
    """Test FlashScore scraper with real data."""
    print_section("TESTING FLASHSCORE SCRAPER")

    scraper = FlashScoreScraper(timeout=30000)

    try:
        print("Testing: scrape_today_matches()")
        matches = await scraper.scrape_today_matches()
        print_data("Today's Matches", matches, max_items=3)

        # Validate format
        if matches:
            match = matches[0]
            required_fields = ['home_team', 'away_team', 'source', 'scraped_at']
            missing = [f for f in required_fields if f not in match]
            if missing:
                print(f"\n⚠️  WARNING: Missing required fields: {missing}")
            else:
                print("\n✅ Format validation: PASSED (all required fields present)")
        else:
            print("\n⚠️  WARNING: No matches returned")

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")


async def test_futbol24() -> None:
    """Test Futbol24 scraper with real data."""
    print_section("TESTING FUTBOL24 SCRAPER")

    scraper = Futbol24Scraper(timeout=30000)

    try:
        print("Testing: scrape_today_matches()")
        matches = await scraper.scrape_today_matches()
        print_data("Today's Matches", matches, max_items=3)

        # Validate format
        if matches:
            match = matches[0]
            required_fields = ['home_team', 'away_team', 'source', 'scraped_at']
            missing = [f for f in required_fields if f not in match]
            if missing:
                print(f"\n⚠️  WARNING: Missing required fields: {missing}")
            else:
                print("\n✅ Format validation: PASSED (all required fields present)")
        else:
            print("\n⚠️  WARNING: No matches returned")

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")


async def test_espn() -> None:
    """Test ESPN scraper with real data."""
    print_section("TESTING ESPN SCRAPER")

    scraper = ESPNScraper(timeout=30000)

    try:
        print("Testing: scrape_soccer_news()")
        articles = await scraper.scrape_soccer_news()
        print_data("Soccer News Articles", articles, max_items=3)

        # Validate format
        if articles:
            article = articles[0]
            required_fields = ['title', 'content', 'source', 'scraped_at']
            missing = [f for f in required_fields if f not in article]
            if missing:
                print(f"\n⚠️  WARNING: Missing required fields: {missing}")
            else:
                print("\n✅ Format validation: PASSED (all required fields present)")
        else:
            print("\n⚠️  WARNING: No articles returned")

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")


async def test_phase2_features() -> None:
    """Test Phase 2 features with sample data."""
    print_section("TESTING PHASE 2 FEATURES (SAMPLE DATA)")

    print("NOTE: Phase 2 features require specific match IDs or team slugs.")
    print("We'll test with placeholder IDs to see the URL construction.\n")

    # FlashScore Phase 2
    print("FlashScore Phase 2 URLs:")
    flashscore = FlashScoreScraper()
    print(f"  Match URL: {flashscore._get_match_url('ABC123')}")

    # Futbol24 Phase 2
    print("\nFutbol24 Phase 2 URLs:")
    futbol24 = Futbol24Scraper()
    print(f"  H2H URL: {futbol24._get_h2h_url('liverpool', 'arsenal')}")
    print(f"  Trends URL: {futbol24._get_trends_url('liverpool')}")

    # ESPN Phase 2
    print("\nESPN Phase 2 URLs:")
    espn = ESPNScraper()
    print(f"  Weather URL: {espn._get_weather_url('ABC123')}")
    print(f"  Injuries URL: {espn._get_injuries_url('liverpool')}")
    print(f"  Predictions URL: {espn._get_expert_predictions_url('ABC123')}")


async def main() -> None:
    """Run all scraper tests."""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "LIVE SCRAPER VALIDATION TEST" + " " * 30 + "║")
    print("╚" + "=" * 78 + "╝")

    print("\nThis script tests scrapers against REAL websites.")
    print("It may take 30-60 seconds per scraper due to anti-detection delays.")
    print("\nStarting tests...\n")

    # Test each scraper
    await test_flashscore()
    await test_futbol24()
    await test_espn()

    # Test Phase 2 URL construction
    await test_phase2_features()

    # Summary
    print_section("TEST SUMMARY")
    print("✅ All scrapers executed (check output above for results)")
    print("\nNOTE: If scrapers returned empty lists, the CSS selectors may need adjustment.")
    print("Check the HTML structure of the actual websites and update selectors accordingly.")
    print("\nNext steps:")
    print("  1. If data was returned: Validate format matches schema")
    print("  2. If no data returned: Inspect actual HTML and fix CSS selectors")
    print("  3. Test Phase 2 features with real match IDs once Phase 1 is validated")


if __name__ == "__main__":
    asyncio.run(main())
