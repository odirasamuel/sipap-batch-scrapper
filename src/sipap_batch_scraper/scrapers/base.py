"""
Base scraper infrastructure with Playwright + stealth mode.

Provides anti-detection capabilities for web scraping sports data sources.
"""

import asyncio
import random
from typing import Final

from playwright.async_api import async_playwright
from playwright_stealth import Stealth  # type: ignore[import-untyped]


class BaseScraper:
    """
    Base scraper with Playwright + stealth mode for anti-detection.

    Features:
    - Headless browser automation with Playwright
    - Stealth mode to evade bot detection
    - User-agent rotation across 10+ real browser signatures
    - Random delays to simulate human behavior
    - Proper resource cleanup on success and failure

    Example:
        >>> scraper = BaseScraper()
        >>> html = await scraper.scrape('https://flashscore.com')
        >>> print(len(html))
        50000
    """

    USER_AGENTS: Final[list[str]] = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',  # noqa: E501
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',  # noqa: E501
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',  # noqa: E501
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',  # noqa: E501
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',  # noqa: E501
        'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',  # noqa: E501
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',  # noqa: E501
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',  # noqa: E501
        'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    ]

    def __init__(self, timeout: int = 15000) -> None:
        """
        Initialize base scraper.

        Args:
            timeout: Page load timeout in milliseconds (default: 15000ms = 15s)
        """
        self.timeout = timeout

    async def scrape(self, url: str) -> str:
        """
        Scrape HTML content from target URL with anti-detection measures.

        Features:
        - Headless Chromium with stealth mode
        - Random user-agent selection
        - Accept-Language header for authenticity
        - Random delay (1.5-3.0s) to simulate human behavior
        - Proper browser cleanup on success and errors

        Args:
            url: Target URL to scrape

        Returns:
            HTML content as string

        Raises:
            TimeoutError: If page load exceeds timeout
            Exception: For other scraping errors

        Example:
            >>> scraper = BaseScraper()
            >>> html = await scraper.scrape('https://flashscore.com/football/')
            >>> 'Premier League' in html
            True
        """
        async with async_playwright() as playwright:
            # Launch headless browser
            browser = await playwright.chromium.launch(headless=True)

            try:
                # Create new page
                page = await browser.new_page()

                # Apply stealth mode to evade detection
                await Stealth().apply_stealth_async(page)

                # Set random user agent and realistic headers
                await page.set_extra_http_headers({
                    'User-Agent': random.choice(self.USER_AGENTS),
                    'Accept-Language': 'en-US,en;q=0.9',
                })

                # Navigate to target URL
                await page.goto(url, timeout=self.timeout)

                # Random delay to simulate human behavior
                await asyncio.sleep(random.uniform(1.5, 3.0))

                # Extract HTML content
                html = await page.content()

                return html

            finally:
                # Always close browser to prevent resource leaks
                await browser.close()
