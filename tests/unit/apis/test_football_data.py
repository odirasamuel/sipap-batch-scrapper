"""Unit tests for FootballDataAPI."""

from unittest.mock import AsyncMock, patch

import pytest

from sipap_batch_scraper.apis.football_data import FootballDataAPI


class TestFootballDataAPI:
    """Test suite for FootballDataAPI."""

    @pytest.fixture
    def api(self) -> FootballDataAPI:
        """Create a FootballDataAPI instance for testing."""
        return FootballDataAPI(api_key="test_api_key_123")

    def test_initialization(self, api: FootballDataAPI) -> None:
        """Test API client initialization."""
        assert api.base_url == "https://api.football-data.org/v4"
        assert api.api_key == "test_api_key_123"

    def test_get_default_headers(self, api: FootballDataAPI) -> None:
        """Test Football-Data.org specific headers."""
        headers = api._get_default_headers()

        assert headers['X-Auth-Token'] == "test_api_key_123"
        assert headers['Accept'] == 'application/json'

    @pytest.mark.asyncio
    async def test_get_competitions(self, api: FootballDataAPI) -> None:
        """Test get_competitions() returns list of competitions."""
        mock_response = {
            'competitions': [
                {'id': 'PL', 'name': 'Premier League', 'area': {'name': 'England'}},
                {'id': 'CL', 'name': 'Champions League', 'area': {'name': 'Europe'}},
            ]
        }

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)):
            competitions = await api.get_competitions()

        assert len(competitions) == 2
        assert competitions[0]['id'] == 'PL'
        assert competitions[0]['name'] == 'Premier League'
        assert competitions[0]['source'] == 'football-data.org'
        assert 'scraped_at' in competitions[0]

    @pytest.mark.asyncio
    async def test_get_competitions_empty_response(self, api: FootballDataAPI) -> None:
        """Test get_competitions() handles empty response."""
        mock_response = {'competitions': []}

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)):
            competitions = await api.get_competitions()

        assert competitions == []

    @pytest.mark.asyncio
    async def test_get_today_matches(self, api: FootballDataAPI) -> None:
        """Test get_today_matches() fetches today's date."""
        mock_response = {
            'matches': [
                {
                    'id': 123,
                    'homeTeam': {'id': 1, 'name': 'Arsenal'},
                    'awayTeam': {'id': 2, 'name': 'Chelsea'},
                    'utcDate': '2026-06-28T15:00:00Z',
                    'status': 'SCHEDULED',
                    'competition': {'id': 'PL', 'name': 'Premier League'},
                }
            ]
        }

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)):
            matches = await api.get_today_matches()

        assert len(matches) == 1
        assert matches[0]['home_team'] == 'Arsenal'
        assert matches[0]['away_team'] == 'Chelsea'

    @pytest.mark.asyncio
    async def test_get_matches_with_date_range(self, api: FootballDataAPI) -> None:
        """Test get_matches() with date range filter."""
        mock_response = {'matches': []}

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            await api.get_matches(date_from='2026-06-01', date_to='2026-06-30')

        # Verify correct params were passed
        call_args = mock_request.call_args
        assert call_args[0][0] == 'GET'  # method
        assert call_args[0][1] == '/matches'  # endpoint
        assert call_args[1]['params']['dateFrom'] == '2026-06-01'
        assert call_args[1]['params']['dateTo'] == '2026-06-30'

    @pytest.mark.asyncio
    async def test_get_matches_with_competition(self, api: FootballDataAPI) -> None:
        """Test get_matches() with competition filter."""
        mock_response = {'matches': []}

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            await api.get_matches(competition_id='PL')

        # Verify competition-specific endpoint
        call_args = mock_request.call_args
        assert call_args[0][1] == '/competitions/PL/matches'

    @pytest.mark.asyncio
    async def test_get_matches_with_status(self, api: FootballDataAPI) -> None:
        """Test get_matches() with status filter."""
        mock_response = {'matches': []}

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            await api.get_matches(status='FINISHED')

        # Verify status param
        call_args = mock_request.call_args
        assert call_args[1]['params']['status'] == 'FINISHED'

    @pytest.mark.asyncio
    async def test_get_match(self, api: FootballDataAPI) -> None:
        """Test get_match() fetches specific match."""
        mock_match = {
            'id': 123,
            'homeTeam': {'id': 1, 'name': 'Arsenal'},
            'awayTeam': {'id': 2, 'name': 'Chelsea'},
            'utcDate': '2026-06-28T15:00:00Z',
            'status': 'IN_PLAY',
            'competition': {'id': 'PL', 'name': 'Premier League'},
            'score': {
                'fullTime': {'home': 2, 'away': 1},
                'halfTime': {'home': 1, 'away': 0},
            },
        }

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_match)) as mock_request:  # noqa: E501
            match = await api.get_match(123)

        mock_request.assert_called_once_with('GET', '/matches/123')
        assert match['external_id'] == '123'
        assert match['home_team'] == 'Arsenal'
        assert match['away_team'] == 'Chelsea'
        assert match['score_home'] == 2
        assert match['score_away'] == 1
        assert match['score_half_home'] == 1
        assert match['score_half_away'] == 0

    @pytest.mark.asyncio
    async def test_get_standings(self, api: FootballDataAPI) -> None:
        """Test get_standings() returns competition standings."""
        mock_response = {
            'standings': [
                {
                    'type': 'TOTAL',
                    'table': [
                        {'position': 1, 'team': {'name': 'Arsenal'}, 'points': 87},
                        {'position': 2, 'team': {'name': 'Man City'}, 'points': 85},
                    ]
                }
            ]
        }

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)):
            standings = await api.get_standings('PL')

        assert len(standings) == 2
        assert standings[0]['position'] == 1
        assert standings[0]['points'] == 87
        assert standings[0]['source'] == 'football-data.org'

    @pytest.mark.asyncio
    async def test_get_standings_fallback_to_first(self, api: FootballDataAPI) -> None:
        """Test get_standings() falls back to first table if no TOTAL type."""
        mock_response = {
            'standings': [
                {
                    'type': 'HOME',
                    'table': [
                        {'position': 1, 'team': {'name': 'Arsenal'}, 'points': 50},
                    ]
                }
            ]
        }

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)):
            standings = await api.get_standings('PL')

        assert len(standings) == 1
        assert standings[0]['position'] == 1

    @pytest.mark.asyncio
    async def test_get_standings_empty_response(self, api: FootballDataAPI) -> None:
        """Test get_standings() handles empty response."""
        mock_response = {'standings': []}

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)):
            standings = await api.get_standings('PL')

        assert standings == []

    @pytest.mark.asyncio
    async def test_get_team(self, api: FootballDataAPI) -> None:
        """Test get_team() fetches team information."""
        mock_team = {
            'id': 133604,
            'name': 'Arsenal',
            'founded': 1886,
            'venue': 'Emirates Stadium',
        }

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_team)) as mock_request:  # noqa: E501
            team = await api.get_team(133604)

        mock_request.assert_called_once_with('GET', '/teams/133604')
        assert team['id'] == 133604
        assert team['name'] == 'Arsenal'
        assert team['source'] == 'football-data.org'

    @pytest.mark.asyncio
    async def test_get_head_to_head_not_implemented(self, api: FootballDataAPI) -> None:
        """Test get_head_to_head() raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="H2H not yet implemented"):
            await api.get_head_to_head(1, 2)

    def test_transform_match_basic(self, api: FootballDataAPI) -> None:
        """Test _transform_match() transforms match data to SIPAP format."""
        raw_match = {
            'id': 123,
            'homeTeam': {'id': 1, 'name': 'Arsenal'},
            'awayTeam': {'id': 2, 'name': 'Chelsea'},
            'utcDate': '2026-06-28T15:00:00Z',
            'status': 'SCHEDULED',
            'competition': {'id': 'PL', 'name': 'Premier League'},
            'season': {'startDate': '2025-08-01'},
            'matchday': 38,
            'stage': 'REGULAR_SEASON',
            'venue': 'Emirates Stadium',
            'score': {},
        }

        transformed = api._transform_match(raw_match)

        assert transformed['external_id'] == '123'
        assert transformed['home_team'] == 'Arsenal'
        assert transformed['home_team_id'] == 1
        assert transformed['away_team'] == 'Chelsea'
        assert transformed['away_team_id'] == 2
        assert transformed['utc_date'] == '2026-06-28T15:00:00Z'
        assert transformed['status'] == 'SCHEDULED'
        assert transformed['competition'] == 'Premier League'
        assert transformed['competition_id'] == 'PL'
        assert transformed['venue'] == 'Emirates Stadium'
        assert transformed['matchday'] == 38
        assert transformed['source'] == 'football-data.org'
        assert 'scraped_at' in transformed

    def test_transform_match_with_scores(self, api: FootballDataAPI) -> None:
        """Test _transform_match() includes scores when available."""
        raw_match = {
            'id': 123,
            'homeTeam': {'id': 1, 'name': 'Arsenal'},
            'awayTeam': {'id': 2, 'name': 'Chelsea'},
            'utcDate': '2026-06-28T15:00:00Z',
            'status': 'FINISHED',
            'competition': {'id': 'PL', 'name': 'Premier League'},
            'score': {
                'fullTime': {'home': 3, 'away': 1},
                'halfTime': {'home': 2, 'away': 0},
            },
        }

        transformed = api._transform_match(raw_match)

        assert transformed['score_home'] == 3
        assert transformed['score_away'] == 1
        assert transformed['score_half_home'] == 2
        assert transformed['score_half_away'] == 0

    def test_transform_match_without_scores(self, api: FootballDataAPI) -> None:
        """Test _transform_match() handles missing scores."""
        raw_match = {
            'id': 123,
            'homeTeam': {'id': 1, 'name': 'Arsenal'},
            'awayTeam': {'id': 2, 'name': 'Chelsea'},
            'utcDate': '2026-06-28T15:00:00Z',
            'status': 'SCHEDULED',
            'competition': {'id': 'PL', 'name': 'Premier League'},
            'score': {},
        }

        transformed = api._transform_match(raw_match)

        # Score fields should not exist
        assert 'score_home' not in transformed
        assert 'score_away' not in transformed
        assert 'score_half_home' not in transformed
        assert 'score_half_away' not in transformed

    @pytest.mark.asyncio
    async def test_close_session(self, api: FootballDataAPI) -> None:
        """Test session cleanup."""
        # Get session to create it
        await api._get_session()
        assert api._session is not None

        # Close session
        await api.close()
        assert api._session.closed
