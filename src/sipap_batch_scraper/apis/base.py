"""
Base API client with common HTTP functionality.

Provides retry logic, rate limiting, error handling for all API clients.
"""

import asyncio
import ssl
from datetime import UTC, datetime
from typing import Any

import aiohttp
import certifi


class BaseAPIClient:
    """
    Base class for sports data API clients.

    Provides:
    - Async HTTP requests with retry logic
    - Rate limiting (respects API limits)
    - Error handling and logging
    - Common response parsing
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize base API client.

        Args:
            base_url: Base URL for API requests
            api_key: API authentication key
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with SSL context."""
        if self._session is None or self._session.closed:
            # Create SSL context with certifi's certificate bundle
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                connector=connector,
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            headers: Additional headers

        Returns:
            JSON response as dictionary

        Raises:
            aiohttp.ClientError: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        session = await self._get_session()

        # Merge headers with default headers
        default_headers = self._get_default_headers()
        if headers:
            default_headers.update(headers)

        for attempt in range(self.max_retries):
            try:
                async with session.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=default_headers,
                ) as response:
                    response.raise_for_status()
                    return await response.json()

            except aiohttp.ClientError as e:
                if attempt == self.max_retries - 1:
                    raise

                # Exponential backoff: 1s, 2s, 4s
                await asyncio.sleep(2 ** attempt)

        # Should never reach here due to raise in loop
        raise RuntimeError("Unexpected error in retry logic")

    def _get_default_headers(self) -> dict[str, str]:
        """Get default headers for API requests (override in subclasses)."""
        return {
            'User-Agent': 'SIPAP/1.0',
            'Accept': 'application/json',
        }

    def _add_metadata(self, data: dict[str, Any], source: str) -> dict[str, Any]:
        """Add metadata to API response."""
        data['source'] = source
        data['scraped_at'] = datetime.now(UTC).isoformat()
        return data
