"""Unit tests for OddsAPI."""

from unittest.mock import AsyncMock, patch

import pytest

from sipap_batch_scraper.apis.odds_api import SPORT_KEYS, OddsAPI


class TestOddsAPI:
    """Test suite for OddsAPI."""

    @pytest.fixture
    def api(self) -> OddsAPI:
        """Create an OddsAPI instance for testing."""
        return OddsAPI(api_key="test_odds_key_123")

    def test_initialization(self, api: OddsAPI) -> None:
        """Test API client initialization."""
        assert api.base_url == "https://api.the-odds-api.com/v4"
        assert api.api_key == "test_odds_key_123"

    @pytest.mark.asyncio
    async def test_get_sports(self, api: OddsAPI) -> None:
        """Test get_sports() returns list of available sports."""
        mock_response = [
            {
                'key': 'soccer_epl',
                'group': 'Soccer',
                'title': 'Premier League',
                'description': 'English Premier League',
                'active': True,
                'has_outrights': False,
            },
            {
                'key': 'soccer_uefa_champs_league',
                'group': 'Soccer',
                'title': 'Champions League',
                'active': True,
                'has_outrights': True,
            },
        ]

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            sports = await api.get_sports()

        # Verify API key passed in params
        call_args = mock_request.call_args
        assert call_args[1]['params']['apiKey'] == 'test_odds_key_123'

        assert len(sports) == 2
        assert sports[0]['key'] == 'soccer_epl'
        assert sports[0]['source'] == 'the-odds-api'
        assert 'scraped_at' in sports[0]

    @pytest.mark.asyncio
    async def test_get_odds_defaults(self, api: OddsAPI) -> None:
        """Test get_odds() with default parameters."""
        mock_response = []

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            await api.get_odds(sport='soccer_epl')

        # Verify correct params
        call_args = mock_request.call_args
        params = call_args[1]['params']
        assert params['apiKey'] == 'test_odds_key_123'
        assert params['regions'] == 'uk,us,eu'
        assert params['markets'] == 'h2h'
        assert params['oddsFormat'] == 'decimal'
        assert params['dateFormat'] == 'iso'

    @pytest.mark.asyncio
    async def test_get_odds_custom_params(self, api: OddsAPI) -> None:
        """Test get_odds() with custom parameters."""
        mock_response = []

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            await api.get_odds(
                sport='soccer_epl',
                regions='uk',
                markets='spreads',
                odds_format='american',
                date_format='unix',
            )

        # Verify custom params
        call_args = mock_request.call_args
        params = call_args[1]['params']
        assert params['regions'] == 'uk'
        assert params['markets'] == 'spreads'
        assert params['oddsFormat'] == 'american'
        assert params['dateFormat'] == 'unix'

    @pytest.mark.asyncio
    async def test_get_odds_transforms_events(self, api: OddsAPI) -> None:
        """Test get_odds() transforms event data."""
        mock_response = [
            {
                'id': 'event_123',
                'sport_key': 'soccer_epl',
                'sport_title': 'Premier League',
                'commence_time': '2026-06-28T15:00:00Z',
                'home_team': 'Arsenal',
                'away_team': 'Chelsea',
                'bookmakers': [
                    {
                        'key': 'bet365',
                        'markets': [
                            {
                                'key': 'h2h',
                                'outcomes': [
                                    {'name': 'Arsenal', 'price': 2.10},
                                    {'name': 'Draw', 'price': 3.50},
                                    {'name': 'Chelsea', 'price': 3.80},
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)):
            odds = await api.get_odds(sport='soccer_epl')

        assert len(odds) == 1
        assert odds[0]['external_id'] == 'event_123'
        assert odds[0]['home_team'] == 'Arsenal'
        assert odds[0]['source'] == 'the-odds-api'

    @pytest.mark.asyncio
    async def test_get_event_odds(self, api: OddsAPI) -> None:
        """Test get_event_odds() fetches specific event."""
        mock_event = {
            'id': 'event_123',
            'sport_key': 'soccer_epl',
            'home_team': 'Arsenal',
            'away_team': 'Chelsea',
            'bookmakers': [],
        }

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_event)) as mock_request:  # noqa: E501
            event = await api.get_event_odds('soccer_epl', 'event_123')

        # Verify correct endpoint
        call_args = mock_request.call_args
        assert call_args[0][1] == '/sports/soccer_epl/events/event_123/odds'
        assert event['external_id'] == 'event_123'

    @pytest.mark.asyncio
    async def test_get_scores(self, api: OddsAPI) -> None:
        """Test get_scores() fetches recent/live scores."""
        mock_response = [
            {
                'id': 'event_123',
                'sport_key': 'soccer_epl',
                'home_team': 'Arsenal',
                'away_team': 'Chelsea',
                'scores': [{'name': 'Arsenal', 'score': '2'}, {'name': 'Chelsea', 'score': '1'}],
            }
        ]

        with patch.object(api, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            scores = await api.get_scores(sport='soccer_epl', days_from=1)

        # Verify params
        call_args = mock_request.call_args
        assert call_args[0][1] == '/sports/soccer_epl/scores'
        assert call_args[1]['params']['daysFrom'] == 1

        assert len(scores) == 1
        assert scores[0]['source'] == 'the-odds-api'

    @pytest.mark.asyncio
    async def test_get_usage(self, api: OddsAPI) -> None:
        """Test get_usage() returns placeholder message."""
        usage = await api.get_usage()

        assert 'message' in usage
        assert usage['source'] == 'the-odds-api'

    def test_transform_odds_basic(self, api: OddsAPI) -> None:
        """Test _transform_odds() transforms event to SIPAP format."""
        raw_event = {
            'id': 'event_123',
            'sport_key': 'soccer_epl',
            'sport_title': 'Premier League',
            'commence_time': '2026-06-28T15:00:00Z',
            'home_team': 'Arsenal',
            'away_team': 'Chelsea',
            'bookmakers': [
                {
                    'key': 'bet365',
                    'markets': [
                        {
                            'key': 'h2h',
                            'outcomes': [
                                {'name': 'Arsenal', 'price': 2.10},
                                {'name': 'Draw', 'price': 3.50},
                                {'name': 'Chelsea', 'price': 3.80},
                            ]
                        }
                    ]
                }
            ]
        }

        transformed = api._transform_odds(raw_event)

        assert transformed['external_id'] == 'event_123'
        assert transformed['sport_key'] == 'soccer_epl'
        assert transformed['sport_title'] == 'Premier League'
        assert transformed['home_team'] == 'Arsenal'
        assert transformed['away_team'] == 'Chelsea'
        assert transformed['num_bookmakers'] == 1
        assert transformed['source'] == 'the-odds-api'
        assert 'scraped_at' in transformed

    def test_transform_odds_calculates_best_odds(self, api: OddsAPI) -> None:
        """Test _transform_odds() calculates best odds across bookmakers."""
        raw_event = {
            'id': 'event_123',
            'home_team': 'Arsenal',
            'away_team': 'Chelsea',
            'bookmakers': [
                {
                    'key': 'bet365',
                    'markets': [
                        {
                            'key': 'h2h',
                            'outcomes': [
                                {'name': 'Arsenal', 'price': 2.10},
                                {'name': 'Draw', 'price': 3.50},
                                {'name': 'Chelsea', 'price': 3.80},
                            ]
                        }
                    ]
                },
                {
                    'key': 'williamhill',
                    'markets': [
                        {
                            'key': 'h2h',
                            'outcomes': [
                                {'name': 'Arsenal', 'price': 2.25},  # Better
                                {'name': 'Draw', 'price': 3.40},
                                {'name': 'Chelsea', 'price': 3.90},  # Better
                            ]
                        }
                    ]
                },
            ]
        }

        transformed = api._transform_odds(raw_event)

        # Best odds should be the maximum across all bookmakers
        assert transformed['best_odds']['home'] == 2.25  # Arsenal (better of 2.10 and 2.25)
        assert transformed['best_odds']['draw'] == 3.50  # Draw (better of 3.50 and 3.40)
        assert transformed['best_odds']['away'] == 3.90  # Chelsea (better of 3.80 and 3.90)

    def test_transform_odds_no_draw(self, api: OddsAPI) -> None:
        """Test _transform_odds() handles sports without draw."""
        raw_event = {
            'id': 'event_123',
            'home_team': 'Lakers',
            'away_team': 'Celtics',
            'bookmakers': [
                {
                    'key': 'bet365',
                    'markets': [
                        {
                            'key': 'h2h',
                            'outcomes': [
                                {'name': 'Lakers', 'price': 1.90},
                                {'name': 'Celtics', 'price': 2.00},
                            ]
                        }
                    ]
                }
            ]
        }

        transformed = api._transform_odds(raw_event)

        assert transformed['best_odds']['home'] == 1.90
        assert transformed['best_odds']['draw'] is None  # No draw in basketball
        assert transformed['best_odds']['away'] == 2.00

    def test_transform_odds_no_bookmakers(self, api: OddsAPI) -> None:
        """Test _transform_odds() handles missing bookmakers."""
        raw_event = {
            'id': 'event_123',
            'home_team': 'Arsenal',
            'away_team': 'Chelsea',
            'bookmakers': []
        }

        transformed = api._transform_odds(raw_event)

        assert transformed['num_bookmakers'] == 0
        assert transformed['best_odds']['home'] == 0.0
        assert transformed['best_odds']['draw'] is None
        assert transformed['best_odds']['away'] == 0.0

    def test_sport_keys_constants(self) -> None:
        """Test SPORT_KEYS constants are available."""
        assert SPORT_KEYS['PREMIER_LEAGUE'] == 'soccer_epl'
        assert SPORT_KEYS['CHAMPIONS_LEAGUE'] == 'soccer_uefa_champs_league'
        assert SPORT_KEYS['LA_LIGA'] == 'soccer_spain_la_liga'
        assert SPORT_KEYS['NBA'] == 'basketball_nba'

    @pytest.mark.asyncio
    async def test_close_session(self, api: OddsAPI) -> None:
        """Test session cleanup."""
        # Get session to create it
        await api._get_session()
        assert api._session is not None

        # Close session
        await api.close()
        assert api._session.closed
