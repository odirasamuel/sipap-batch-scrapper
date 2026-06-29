#!/usr/bin/env python3
"""
HTML inspection script for scraper debugging.

Fetches actual HTML from websites and saves it for inspection.
This helps us identify the correct CSS selectors.

Usage:
    python inspect_html.py
"""

import asyncio
from pathlib import Path

from sipap_batch_scraper.scrapers.base import BaseScraper


async def fetch_and_save(url: str, filename: str, timeout: int = 60000) -> None:
    """Fetch HTML from URL and save to file."""
    print(f"\nFetching: {url}")
    print(f"Timeout: {timeout}ms")

    scraper = BaseScraper(timeout=timeout)

    try:
        html = await scraper.scrape(url)

        # Save to file
        output_dir = Path("html_samples")
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / filename
        output_file.write_text(html, encoding='utf-8')

        print(f"✅ Saved: {output_file} ({len(html):,} characters)")

        # Show a preview
        lines = html.split('\n')[:50]
        print(f"\nFirst 50 lines preview:")
        print("-" * 80)
        for i, line in enumerate(lines, 1):
            print(f"{i:3d}: {line[:100]}")
        print("-" * 80)

    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")


async def main() -> None:
    """Fetch HTML from all three sites."""
    print("=" * 80)
    print("  HTML INSPECTION SCRIPT")
    print("=" * 80)
    print("\nThis script fetches actual HTML from sports sites.")
    print("The HTML will be saved to html_samples/ directory for inspection.\n")

    # FlashScore
    await fetch_and_save(
        url="https://www.flashscore.com/football/",
        filename="flashscore_football.html",
        timeout=60000  # 60 seconds
    )

    # Futbol24
    await fetch_and_save(
        url="https://www.futbol24.com/live/",
        filename="futbol24_live.html",
        timeout=60000
    )

    # ESPN
    await fetch_and_save(
        url="https://www.espn.com/soccer/",
        filename="espn_soccer.html",
        timeout=60000
    )

    print("\n" + "=" * 80)
    print("  INSPECTION COMPLETE")
    print("=" * 80)
    print("\nHTML files saved to: html_samples/")
    print("\nNext steps:")
    print("  1. Open the HTML files in a text editor")
    print("  2. Search for match/news data in the HTML")
    print("  3. Identify the actual CSS class names and structure")
    print("  4. Update scrapers with correct selectors")
    print("\nExample commands:")
    print("  grep -i 'class=' html_samples/flashscore_football.html | head -20")
    print("  grep -i 'match' html_samples/futbol24_live.html | head -20")
    print("  grep -i 'article' html_samples/espn_soccer.html | head -20")


if __name__ == "__main__":
    asyncio.run(main())
