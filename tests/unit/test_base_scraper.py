"""
Unit tests for base scraper infrastructure.

Following TDD methodology: RED phase - these tests will fail until implementation.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from sipap_batch_scraper.scrapers.base import BaseScraper


class TestBaseScraper:
    """Test suite for BaseScraper class."""

    @pytest.mark.asyncio
    async def test_scrape_returns_html_content(self) -> None:
        """Test that scrape() returns HTML content from target URL."""
        scraper = BaseScraper()

        with patch('sipap_batch_scraper.scrapers.base.async_playwright') as mock_playwright:
            # Mock Playwright components
            mock_page = AsyncMock()
            mock_page.content.return_value = '<html><body>Test Content</body></html>'
            mock_browser = AsyncMock()
            mock_browser.new_page.return_value = mock_page
            mock_context = AsyncMock()
            mock_context.chromium.launch.return_value = mock_browser
            mock_playwright.return_value.__aenter__.return_value = mock_context

            result = await scraper.scrape('https://example.com')

            assert result == '<html><body>Test Content</body></html>'
            mock_context.chromium.launch.assert_called_once()
            mock_page.goto.assert_called_once()

    @pytest.mark.asyncio
    async def test_scrape_uses_stealth_mode(self) -> None:
        """Test that scraper applies stealth mode to evade detection."""
        scraper = BaseScraper()

        with patch('sipap_batch_scraper.scrapers.base.async_playwright') as mock_playwright, \
             patch('sipap_batch_scraper.scrapers.base.Stealth') as mock_stealth_class:

            mock_page = AsyncMock()
            mock_page.content.return_value = '<html></html>'
            mock_browser = AsyncMock()
            mock_browser.new_page.return_value = mock_page
            mock_context = AsyncMock()
            mock_context.chromium.launch.return_value = mock_browser
            mock_playwright.return_value.__aenter__.return_value = mock_context

            # Mock the Stealth instance and its apply_stealth_async method
            mock_stealth_instance = Mock()
            mock_stealth_instance.apply_stealth_async = AsyncMock()
            mock_stealth_class.return_value = mock_stealth_instance

            await scraper.scrape('https://example.com')

            # Verify stealth mode was applied
            mock_stealth_instance.apply_stealth_async.assert_called_once_with(mock_page)

    @pytest.mark.asyncio
    async def test_scrape_rotates_user_agents(self) -> None:
        """Test that scraper rotates user agents across requests."""
        scraper = BaseScraper()
        user_agents_used = set()

        with patch('sipap_batch_scraper.scrapers.base.async_playwright') as mock_playwright:
            mock_page = AsyncMock()
            mock_page.content.return_value = '<html></html>'
            mock_browser = AsyncMock()
            mock_browser.new_page.return_value = mock_page
            mock_context = AsyncMock()
            mock_context.chromium.launch.return_value = mock_browser
            mock_playwright.return_value.__aenter__.return_value = mock_context

            # Make multiple requests
            for _ in range(10):
                await scraper.scrape('https://example.com')
                # Extract user agent from set_extra_http_headers call
                calls = mock_page.set_extra_http_headers.call_args_list
                if calls:
                    headers = calls[-1][0][0]
                    user_agents_used.add(headers.get('User-Agent', ''))

            # Should have used multiple user agents
            assert len(user_agents_used) > 1

    @pytest.mark.asyncio
    async def test_scrape_applies_random_delay(self) -> None:
        """Test that scraper applies random delay to avoid detection."""
        scraper = BaseScraper()

        with patch('sipap_batch_scraper.scrapers.base.async_playwright') as mock_playwright, \
             patch('sipap_batch_scraper.scrapers.base.asyncio.sleep') as mock_sleep:

            mock_page = AsyncMock()
            mock_page.content.return_value = '<html></html>'
            mock_browser = AsyncMock()
            mock_browser.new_page.return_value = mock_page
            mock_context = AsyncMock()
            mock_context.chromium.launch.return_value = mock_browser
            mock_playwright.return_value.__aenter__.return_value = mock_context

            await scraper.scrape('https://example.com')

            # Verify sleep was called with a value between 1.5 and 3.0
            mock_sleep.assert_called_once()
            delay = mock_sleep.call_args[0][0]
            assert 1.5 <= delay <= 3.0

    @pytest.mark.asyncio
    async def test_scrape_handles_timeout_gracefully(self) -> None:
        """Test that scraper handles page timeout errors."""
        scraper = BaseScraper()

        with patch('sipap_batch_scraper.scrapers.base.async_playwright') as mock_playwright:
            mock_page = AsyncMock()
            mock_page.goto.side_effect = TimeoutError("Page load timeout")
            mock_browser = AsyncMock()
            mock_browser.new_page.return_value = mock_page
            mock_context = AsyncMock()
            mock_context.chromium.launch.return_value = mock_browser
            mock_playwright.return_value.__aenter__.return_value = mock_context

            with pytest.raises(TimeoutError):
                await scraper.scrape('https://example.com')

    @pytest.mark.asyncio
    async def test_scrape_closes_browser_after_completion(self) -> None:
        """Test that browser is properly closed after scraping."""
        scraper = BaseScraper()

        with patch('sipap_batch_scraper.scrapers.base.async_playwright') as mock_playwright:
            mock_page = AsyncMock()
            mock_page.content.return_value = '<html></html>'
            mock_browser = AsyncMock()
            mock_browser.new_page.return_value = mock_page
            mock_context = AsyncMock()
            mock_context.chromium.launch.return_value = mock_browser
            mock_playwright.return_value.__aenter__.return_value = mock_context

            await scraper.scrape('https://example.com')

            mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_scrape_closes_browser_on_error(self) -> None:
        """Test that browser is closed even if scraping fails."""
        scraper = BaseScraper()

        with patch('sipap_batch_scraper.scrapers.base.async_playwright') as mock_playwright:
            mock_page = AsyncMock()
            mock_page.content.side_effect = Exception("Scraping error")
            mock_browser = AsyncMock()
            mock_browser.new_page.return_value = mock_page
            mock_context = AsyncMock()
            mock_context.chromium.launch.return_value = mock_browser
            mock_playwright.return_value.__aenter__.return_value = mock_context

            with pytest.raises(Exception):
                await scraper.scrape('https://example.com')

            mock_browser.close.assert_called_once()

    def test_user_agents_list_is_comprehensive(self) -> None:
        """Test that scraper has a comprehensive list of user agents."""
        scraper = BaseScraper()

        # Should have at least 10 different user agents
        assert len(scraper.USER_AGENTS) >= 10

        # Each should be a realistic browser user agent
        for ua in scraper.USER_AGENTS:
            assert 'Mozilla' in ua
            assert len(ua) > 50  # Realistic user agents are long

    def test_default_timeout_is_reasonable(self) -> None:
        """Test that default page load timeout is set reasonably."""
        scraper = BaseScraper()

        # Should have a timeout value (in milliseconds)
        assert hasattr(scraper, 'timeout')
        assert scraper.timeout >= 10000  # At least 10 seconds
        assert scraper.timeout <= 30000  # Not more than 30 seconds
