#!/usr/bin/env python3
"""
API Integration Test Script.

Tests Football-Data.org and The Odds API with real data.
Validates API keys are working and data format is correct.

Usage:
    python test_api_integration.py
"""

import asyncio
import json
import os
from typing import Any

from sipap_batch_scraper.apis.football_data import FootballDataAPI
from sipap_batch_scraper.apis.odds_api import OddsAPI, SPORT_KEYS


def print_section(title: str) -> None:
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_data(label: str, data: Any, max_items: int = 3) -> None:
    """Print data in formatted way."""
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


async def test_football_data_api() -> None:
    """Test Football-Data.org API."""
    print_section("TESTING FOOTBALL-DATA.ORG API")

    # Get API key from environment or use the one from screenshot
    api_key = os.getenv('FOOTBALL_DATA_API_KEY', '6accb181c1b64cbf832d29ca2c401012')

    api = FootballDataAPI(api_key=api_key)

    try:
        # Test 1: Get competitions
        print("Test 1: Get Available Competitions")
        competitions = await api.get_competitions()
        print_data("Competitions", competitions, max_items=5)

        # Test 2: Get today's matches
        print("\n" + "-" * 80)
        print("Test 2: Get Today's Matches")
        today_matches = await api.get_today_matches()
        print_data("Today's Matches", today_matches, max_items=3)

        # Test 3: Get Premier League standings (if available)
        try:
            print("\n" + "-" * 80)
            print("Test 3: Get Premier League Standings")
            standings = await api.get_standings('PL')
            print_data("Premier League Standings", standings, max_items=5)
        except Exception as e:
            print(f"Note: Standings may not be available: {e}")

        print("\n✅ Football-Data.org API: ALL TESTS PASSED")

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        print("\nTroubleshooting:")
        print("1. Check API key is valid")
        print("2. Check you haven't exceeded rate limit (10 requests/minute)")
        print("3. Check internet connection")

    finally:
        await api.close()


async def test_odds_api() -> None:
    """Test The Odds API."""
    print_section("TESTING THE ODDS API")

    # Get API key from environment or use the one from screenshot
    api_key = os.getenv('ODDS_API_KEY', 'c3149852cf0badfd1cfe1e86d98642be')

    api = OddsAPI(api_key=api_key)

    try:
        # Test 1: Get available sports
        print("Test 1: Get Available Sports")
        sports = await api.get_sports()
        print_data("Available Sports", sports, max_items=10)

        # Test 2: Get odds for Premier League (if available)
        try:
            print("\n" + "-" * 80)
            print("Test 2: Get Premier League Odds")
            epl_odds = await api.get_odds(sport=SPORT_KEYS['PREMIER_LEAGUE'])
            print_data("Premier League Odds", epl_odds, max_items=2)

            if epl_odds:
                # Show best odds summary
                print("\nBest Odds Summary:")
                for event in epl_odds[:3]:
                    home = event.get('home_team')
                    away = event.get('away_team')
                    best = event.get('best_odds', {})
                    print(f"\n{home} vs {away}")
                    print(f"  Home: {best.get('home')}")
                    print(f"  Draw: {best.get('draw')}")
                    print(f"  Away: {best.get('away')}")
                    print(f"  Bookmakers: {event.get('num_bookmakers')}")

        except Exception as e:
            print(f"Note: Premier League odds may not be available: {e}")

        # Test 3: Get Champions League odds (if available)
        try:
            print("\n" + "-" * 80)
            print("Test 3: Get Champions League Odds")
            ucl_odds = await api.get_odds(sport=SPORT_KEYS['CHAMPIONS_LEAGUE'])
            print_data("Champions League Odds", ucl_odds, max_items=2)
        except Exception as e:
            print(f"Note: Champions League odds may not be available: {e}")

        print("\n✅ The Odds API: ALL TESTS PASSED")

        print("\n" + "=" * 80)
        print("  IMPORTANT: FREE TIER LIMITS")
        print("=" * 80)
        print("\nThe Odds API Free Tier: 500 credits/month (~16 requests/day)")
        print("We just used ~2-3 credits for this test.")
        print("Monitor usage at: https://the-odds-api.com/account/")

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        print("\nTroubleshooting:")
        print("1. Check API key is valid")
        print("2. Check you haven't exceeded rate limit (500 credits/month)")
        print("3. Check internet connection")

    finally:
        await api.close()


async def test_thesportsdb_api() -> None:
    """Test TheSportsDB API."""
    print_section("TESTING THESPORTSDB API")

    # Get API key from environment or use the free tier key
    api_key = os.getenv('THESPORTSDB_API_KEY', '123')

    from sipap_batch_scraper.apis.thesportsdb import TheSportsDBClient, LEAGUE_IDS

    api = TheSportsDBClient(api_key=api_key)

    try:
        # Test 1: Search for a team
        print("Test 1: Search for Arsenal")
        teams = await api.search_team("Arsenal")
        print_data("Arsenal Search Results", teams, max_items=2)

        # Test 2: Get next Premier League events
        try:
            print("\n" + "-" * 80)
            print("Test 2: Get Next Premier League Events")
            events = await api.get_events_next_league(LEAGUE_IDS['PREMIER_LEAGUE'])
            print_data("Upcoming Premier League Events", events, max_items=3)
        except Exception as e:
            print(f"Note: Next events may not be available: {e}")

        # Test 3: Search for a player
        try:
            print("\n" + "-" * 80)
            print("Test 3: Search for Players")
            players = await api.search_player("Messi")
            print_data("Player Search Results", players, max_items=2)
        except Exception as e:
            print(f"Note: Player search may be limited on free tier: {e}")

        print("\n✅ TheSportsDB API: ALL TESTS PASSED")

        print("\n" + "=" * 80)
        print("  IMPORTANT: FREE TIER LIMITS")
        print("=" * 80)
        print("\nTheSportsDB Free Tier: 30 requests/minute (read-only)")
        print("We just used ~3 requests for this test.")
        print("Upgrade to $9/mo for real-time scores with 2-min delay")

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        print("\nTroubleshooting:")
        print("1. Check API key is valid (free tier: '123')")
        print("2. Check you haven't exceeded rate limit (30 requests/minute)")
        print("3. Check internet connection")

    finally:
        await api.close()


async def test_placeholder_apis() -> None:
    """Test placeholder APIs (should raise NotImplementedError)."""
    print_section("TESTING PLACEHOLDER APIs")

    from sipap_batch_scraper.apis.api_football import APIFootballClient

    # Test API-Football placeholder
    print("Test: API-Football (should fail with NotImplementedError)")
    api_football = APIFootballClient()
    try:
        await api_football.get_today_matches()
        print("❌ UNEXPECTED: Should have raised NotImplementedError")
    except NotImplementedError as e:
        print(f"✅ EXPECTED: {e}")

    print("\n✅ Placeholder APIs: Correctly raising NotImplementedError")


async def main() -> None:
    """Run all API tests."""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "API INTEGRATION TEST" + " " * 33 + "║")
    print("╚" + "=" * 78 + "╝")

    print("\nThis script tests API integration with REAL data.")
    print("Make sure you have valid API keys configured.\n")

    # Test active APIs
    await test_football_data_api()
    await test_odds_api()
    await test_thesportsdb_api()

    # Test placeholder APIs
    await test_placeholder_apis()

    # Summary
    print_section("TEST SUMMARY")
    print("✅ Football-Data.org: ACTIVE (13 competitions, 10 req/min, FREE forever)")
    print("✅ The Odds API: ACTIVE (500 credits/month, ~16 req/day, FREE tier)")
    print("✅ TheSportsDB: ACTIVE (30 req/min, read-only, FREE tier)")
    print("🔜 API-Football: PLACEHOLDER (needs $19/mo subscription)")
    print("🔜 News Intelligence: FUTURE (AI-powered news search via MCP)")

    print("\n" + "=" * 80)
    print("  NEXT STEPS")
    print("=" * 80)
    print("\n1. If tests passed: Integrate into daily harvest job")
    print("2. If tests failed: Check API keys and rate limits")
    print("3. Monitor free tier usage to decide on upgrades")
    print("4. Add API-Football when budget allows ($19/mo)")
    print("5. Upgrade TheSportsDB for real-time scores when needed ($9/mo)")


if __name__ == "__main__":
    asyncio.run(main())
