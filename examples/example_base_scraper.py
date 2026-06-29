"""
Example: Using BaseScraper to scrape sports data.

Demonstrates:
- Basic HTML scraping with Playwright
- Anti-detection features (stealth mode, user-agent rotation)
- Proper resource cleanup
"""

import asyncio

from sipap_batch_scraper.scrapers.base import BaseScraper


async def main() -> None:
    """Demonstrate base scraper usage."""
    print("=== BaseScraper Example ===\n")

    # Initialize scraper with 20-second timeout
    scraper = BaseScraper(timeout=20000)

    # Example 1: Scrape FlashScore homepage
    print("1. Scraping FlashScore homepage...")
    try:
        html = await scraper.scrape('https://www.flashscore.com/football/')
        print(f"   ✓ Successfully scraped {len(html)} characters")
        print(f"   ✓ Contains 'Premier League': {'Premier League' in html}")
        print(f"   ✓ Contains 'La Liga': {'La Liga' in html}\n")
    except Exception as e:
        print(f"   ✗ Error: {e}\n")

    # Example 2: Scrape with stealth mode (happens automatically)
    print("2. Scraping with anti-detection features...")
    print("   - Stealth mode: Enabled (automatic)")
    print("   - User-agent: Random rotation across 12 signatures")
    print("   - Delay: Random 1.5-3.0s between requests")
    print("   - Headers: Realistic Accept-Language, etc.\n")

    # Example 3: Multiple scrapes (demonstrates rotation)
    print("3. Multiple scrapes (shows user-agent rotation)...")
    urls = [
        'https://www.flashscore.com/',
        'https://www.futbol24.com/',
        'https://www.espn.com/soccer/'
    ]

    for i, url in enumerate(urls, 1):
        try:
            html = await scraper.scrape(url)
            print(f"   ✓ Scrape {i}: {url} - {len(html)} chars")
        except Exception as e:
            print(f"   ✗ Scrape {i}: {url} - Error: {e}")

    print("\n=== Example Complete ===")


if __name__ == '__main__':
    # Note: This requires Playwright browsers to be installed
    # Run: playwright install chromium
    asyncio.run(main())
