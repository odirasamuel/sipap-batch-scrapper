"""Unit tests for BaseAPIClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from sipap_batch_scraper.apis.base import BaseAPIClient


class TestBaseAPIClient:
    """Test suite for BaseAPIClient."""

    @pytest.fixture
    def client(self) -> BaseAPIClient:
        """Create a BaseAPIClient instance for testing."""
        return BaseAPIClient(
            base_url="https://api.example.com/v1",
            api_key="test_key_123",
            timeout=30,
            max_retries=3,
        )

    def test_initialization(self, client: BaseAPIClient) -> None:
        """Test client initialization."""
        assert client.base_url == "https://api.example.com/v1"
        assert client.api_key == "test_key_123"
        assert client.timeout.total == 30
        assert client.max_retries == 3
        assert client._session is None

    def test_base_url_strips_trailing_slash(self) -> None:
        """Test that trailing slash is removed from base URL."""
        client = BaseAPIClient(
            base_url="https://api.example.com/v1/",
            api_key="test_key",
        )
        assert client.base_url == "https://api.example.com/v1"

    @pytest.mark.asyncio
    async def test_get_session_creates_new_session(self, client: BaseAPIClient) -> None:
        """Test that _get_session creates a new session if none exists."""
        session = await client._get_session()

        assert session is not None
        assert isinstance(session, aiohttp.ClientSession)
        assert client._session is session

        await client.close()

    @pytest.mark.asyncio
    async def test_get_session_reuses_existing_session(self, client: BaseAPIClient) -> None:
        """Test that _get_session reuses existing session."""
        session1 = await client._get_session()
        session2 = await client._get_session()

        assert session1 is session2

        await client.close()

    @pytest.mark.asyncio
    async def test_close_closes_session(self, client: BaseAPIClient) -> None:
        """Test that close() closes the HTTP session."""
        session = await client._get_session()
        assert not session.closed

        await client.close()
        assert session.closed

    @pytest.mark.asyncio
    async def test_close_handles_no_session(self, client: BaseAPIClient) -> None:
        """Test that close() handles case where no session exists."""
        # Should not raise an exception
        await client.close()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_request_success(self, client: BaseAPIClient) -> None:
        """Test successful HTTP request."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={'data': 'test_data'})
        mock_response.raise_for_status = MagicMock()

        mock_session = AsyncMock()
        mock_session.request = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Mock request context manager
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch.object(client, '_get_session', return_value=mock_session):
            result = await client._request('GET', '/test')

        assert result == {'data': 'test_data'}
        mock_response.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_retry_on_failure(self, client: BaseAPIClient) -> None:
        """Test HTTP request retries on failure."""
        # First two attempts fail, third succeeds
        mock_failed_response = AsyncMock()
        mock_failed_response.raise_for_status = MagicMock(
            side_effect=aiohttp.ClientError("Connection error")
        )
        mock_failed_response.__aenter__ = AsyncMock(return_value=mock_failed_response)
        mock_failed_response.__aexit__ = AsyncMock(return_value=None)

        mock_success_response = AsyncMock()
        mock_success_response.json = AsyncMock(return_value={'data': 'success'})
        mock_success_response.raise_for_status = MagicMock()
        mock_success_response.__aenter__ = AsyncMock(return_value=mock_success_response)
        mock_success_response.__aexit__ = AsyncMock(return_value=None)

        call_count = 0

        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return mock_failed_response
            return mock_success_response

        mock_session = AsyncMock()
        mock_session.request = MagicMock(side_effect=mock_request)

        # Mock sleep to avoid actual delays
        with patch.object(client, '_get_session', return_value=mock_session):
            with patch('asyncio.sleep', new=AsyncMock()):
                result = await client._request('GET', '/test')

        assert result == {'data': 'success'}
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_request_fails_after_max_retries(self, client: BaseAPIClient) -> None:
        """Test HTTP request fails after max retries."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=aiohttp.ClientError("Connection error")
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.request = MagicMock(return_value=mock_response)

        with patch.object(client, '_get_session', return_value=mock_session):
            with patch('asyncio.sleep', new=AsyncMock()):
                with pytest.raises(aiohttp.ClientError, match="Connection error"):
                    await client._request('GET', '/test')

    @pytest.mark.asyncio
    async def test_request_exponential_backoff(self, client: BaseAPIClient) -> None:
        """Test exponential backoff on retries."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=aiohttp.ClientError("Connection error")
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.request = MagicMock(return_value=mock_response)

        sleep_times = []

        async def mock_sleep(duration):
            sleep_times.append(duration)

        with patch.object(client, '_get_session', return_value=mock_session):
            with patch('asyncio.sleep', new=mock_sleep):
                with pytest.raises(aiohttp.ClientError):
                    await client._request('GET', '/test')

        # Verify exponential backoff: 1s (2^0), 2s (2^1), 4s (2^2)
        # Only 2 sleeps for 3 retries (no sleep after last attempt)
        assert sleep_times == [1, 2]

    @pytest.mark.asyncio
    async def test_request_builds_correct_url(self, client: BaseAPIClient) -> None:
        """Test request builds correct URL from base_url and endpoint."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()

        captured_url = None

        def capture_url(method, url, **kwargs):
            nonlocal captured_url
            captured_url = url
            return mock_response

        mock_session.request = MagicMock(side_effect=capture_url)

        with patch.object(client, '_get_session', return_value=mock_session):
            await client._request('GET', '/path/to/resource')

        assert captured_url == "https://api.example.com/v1/path/to/resource"

    @pytest.mark.asyncio
    async def test_request_handles_leading_slash(self, client: BaseAPIClient) -> None:
        """Test request handles endpoint with leading slash."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()

        captured_url = None

        def capture_url(method, url, **kwargs):
            nonlocal captured_url
            captured_url = url
            return mock_response

        mock_session.request = MagicMock(side_effect=capture_url)

        with patch.object(client, '_get_session', return_value=mock_session):
            await client._request('GET', '/test')

        # Should not have double slash
        assert captured_url == "https://api.example.com/v1/test"

    @pytest.mark.asyncio
    async def test_request_merges_headers(self, client: BaseAPIClient) -> None:
        """Test request merges custom headers with default headers."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()

        captured_headers = None

        def capture_headers(method, url, headers=None, **kwargs):
            nonlocal captured_headers
            captured_headers = headers
            return mock_response

        mock_session.request = MagicMock(side_effect=capture_headers)

        custom_headers = {'X-Custom-Header': 'custom_value'}

        with patch.object(client, '_get_session', return_value=mock_session):
            await client._request('GET', '/test', headers=custom_headers)

        assert captured_headers['User-Agent'] == 'SIPAP/1.0'
        assert captured_headers['Accept'] == 'application/json'
        assert captured_headers['X-Custom-Header'] == 'custom_value'

    @pytest.mark.asyncio
    async def test_request_passes_params(self, client: BaseAPIClient) -> None:
        """Test request passes query parameters."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={})
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()

        captured_params = None

        def capture_params(method, url, params=None, **kwargs):
            nonlocal captured_params
            captured_params = params
            return mock_response

        mock_session.request = MagicMock(side_effect=capture_params)

        params = {'key1': 'value1', 'key2': 'value2'}

        with patch.object(client, '_get_session', return_value=mock_session):
            await client._request('GET', '/test', params=params)

        assert captured_params == params

    def test_get_default_headers(self, client: BaseAPIClient) -> None:
        """Test default headers."""
        headers = client._get_default_headers()

        assert headers['User-Agent'] == 'SIPAP/1.0'
        assert headers['Accept'] == 'application/json'

    def test_add_metadata(self, client: BaseAPIClient) -> None:
        """Test _add_metadata adds source and timestamp."""
        data = {'key': 'value'}
        result = client._add_metadata(data, 'test-source')

        assert result['key'] == 'value'
        assert result['source'] == 'test-source'
        assert 'scraped_at' in result
        # Verify ISO 8601 format
        assert 'T' in result['scraped_at']
        assert result['scraped_at'].endswith('Z') or '+' in result['scraped_at']
