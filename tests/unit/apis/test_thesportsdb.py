"""Unit tests for TheSportsDBClient."""

from unittest.mock import AsyncMock, patch

import pytest

from sipap_batch_scraper.apis.thesportsdb import LEAGUE_IDS, TheSportsDBClient


class TestTheSportsDBClient:
    """Test suite for TheSportsDBClient."""

    @pytest.fixture
    def client(self) -> TheSportsDBClient:
        """Create a TheSportsDBClient instance for testing."""
        return TheSportsDBClient(api_key="123")

    def test_initialization_default_key(self) -> None:
        """Test client initialization with default free tier key."""
        client = TheSportsDBClient()

        assert client.base_url == "https://www.thesportsdb.com/api/v1/json/123"
        assert client.api_key == "123"

    def test_initialization_custom_key(self) -> None:
        """Test client initialization with custom API key."""
        client = TheSportsDBClient(api_key="paid_key_456")

        assert client.base_url == "https://www.thesportsdb.com/api/v1/json/paid_key_456"
        assert client.api_key == "paid_key_456"

    @pytest.mark.asyncio
    async def test_search_team(self, client: TheSportsDBClient) -> None:
        """Test search_team() returns team search results."""
        mock_response = {
            'teams': [
                {
                    'idTeam': '133604',
                    'strTeam': 'Arsenal',
                    'strLeague': 'Premier League',
                    'strStadium': 'Emirates Stadium',
                    'intFormedYear': '1886',
                    'strCountry': 'England',
                    'strBadge': 'https://example.com/arsenal.png',
                }
            ]
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            teams = await client.search_team('Arsenal')

        # Verify correct endpoint and params
        call_args = mock_request.call_args
        assert call_args[0][1] == '/searchteams.php'
        assert call_args[1]['params']['t'] == 'Arsenal'

        assert len(teams) == 1
        assert teams[0]['idTeam'] == '133604'
        assert teams[0]['strTeam'] == 'Arsenal'
        assert teams[0]['source'] == 'thesportsdb'
        assert 'scraped_at' in teams[0]

    @pytest.mark.asyncio
    async def test_search_team_no_results(self, client: TheSportsDBClient) -> None:
        """Test search_team() handles no results."""
        mock_response = {'teams': None}

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)):
            teams = await client.search_team('NonexistentTeam')

        assert teams == []

    @pytest.mark.asyncio
    async def test_get_team(self, client: TheSportsDBClient) -> None:
        """Test get_team() fetches team by ID."""
        mock_response = {
            'teams': [
                {
                    'idTeam': '133604',
                    'strTeam': 'Arsenal',
                    'strDescriptionEN': 'Arsenal Football Club is an English professional football club...',  # noqa: E501
                }
            ]
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            team = await client.get_team(133604)

        # Verify correct endpoint
        call_args = mock_request.call_args
        assert call_args[0][1] == '/lookupteam.php'
        assert call_args[1]['params']['id'] == 133604

        assert team['idTeam'] == '133604'
        assert team['source'] == 'thesportsdb'

    @pytest.mark.asyncio
    async def test_get_team_not_found(self, client: TheSportsDBClient) -> None:
        """Test get_team() handles team not found."""
        mock_response = {'teams': None}

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)):
            team = await client.get_team(999999)

        assert team == {}

    @pytest.mark.asyncio
    async def test_search_player(self, client: TheSportsDBClient) -> None:
        """Test search_player() returns player search results."""
        mock_response = {
            'player': [
                {
                    'idPlayer': '34145937',
                    'strPlayer': 'Lionel Messi',
                    'strTeam': 'Inter Miami',
                    'strPosition': 'Forward',
                }
            ]
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            players = await client.search_player('Messi')

        # Verify correct endpoint and params
        call_args = mock_request.call_args
        assert call_args[0][1] == '/searchplayers.php'
        assert call_args[1]['params']['p'] == 'Messi'

        assert len(players) == 1
        assert players[0]['idPlayer'] == '34145937'
        assert players[0]['source'] == 'thesportsdb'

    @pytest.mark.asyncio
    async def test_search_player_no_results(self, client: TheSportsDBClient) -> None:
        """Test search_player() handles no results."""
        mock_response = {'player': None}

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)):
            players = await client.search_player('NonexistentPlayer')

        assert players == []

    @pytest.mark.asyncio
    async def test_get_player(self, client: TheSportsDBClient) -> None:
        """Test get_player() fetches player by ID."""
        mock_response = {
            'players': [
                {
                    'idPlayer': '34145937',
                    'strPlayer': 'Lionel Messi',
                    'dateBorn': '1987-06-24',
                }
            ]
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            player = await client.get_player(34145937)

        # Verify correct endpoint
        call_args = mock_request.call_args
        assert call_args[0][1] == '/lookupplayer.php'
        assert call_args[1]['params']['id'] == 34145937

        assert player['idPlayer'] == '34145937'
        assert player['source'] == 'thesportsdb'

    @pytest.mark.asyncio
    async def test_get_player_not_found(self, client: TheSportsDBClient) -> None:
        """Test get_player() handles player not found."""
        mock_response = {'players': None}

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)):
            player = await client.get_player(999999)

        assert player == {}

    @pytest.mark.asyncio
    async def test_get_events_next_league(self, client: TheSportsDBClient) -> None:
        """Test get_events_next_league() fetches upcoming events."""
        mock_response = {
            'events': [
                {
                    'idEvent': '123456',
                    'strHomeTeam': 'Arsenal',
                    'strAwayTeam': 'Chelsea',
                    'dateEvent': '2026-06-30',
                    'strTime': '19:00:00',
                }
            ]
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            events = await client.get_events_next_league(4328)  # Premier League

        # Verify correct endpoint
        call_args = mock_request.call_args
        assert call_args[0][1] == '/eventsnextleague.php'
        assert call_args[1]['params']['id'] == 4328

        assert len(events) == 1
        assert events[0]['idEvent'] == '123456'
        assert events[0]['source'] == 'thesportsdb'

    @pytest.mark.asyncio
    async def test_get_events_next_league_no_results(self, client: TheSportsDBClient) -> None:
        """Test get_events_next_league() handles no upcoming events."""
        mock_response = {'events': None}

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)):
            events = await client.get_events_next_league(4328)

        assert events == []

    @pytest.mark.asyncio
    async def test_get_events(self, client: TheSportsDBClient) -> None:
        """Test get_events() fetches season events."""
        mock_response = {
            'events': [
                {
                    'idEvent': '123456',
                    'strSeason': '2025-2026',
                    'strHomeTeam': 'Arsenal',
                    'strAwayTeam': 'Chelsea',
                }
            ]
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            events = await client.get_events(4328, '2025-2026')

        # Verify correct params
        call_args = mock_request.call_args
        assert call_args[0][1] == '/eventsseason.php'
        assert call_args[1]['params']['id'] == 4328
        assert call_args[1]['params']['s'] == '2025-2026'

        assert len(events) == 1
        assert events[0]['source'] == 'thesportsdb'

    @pytest.mark.asyncio
    async def test_get_league_standings(self, client: TheSportsDBClient) -> None:
        """Test get_league_standings() fetches standings."""
        mock_response = {
            'table': [
                {
                    'idTeam': '133604',
                    'strTeam': 'Arsenal',
                    'intRank': '1',
                    'intPoints': '87',
                    'intWin': '27',
                    'intDraw': '6',
                    'intLoss': '5',
                }
            ]
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            standings = await client.get_league_standings(4328, '2025-2026')

        # Verify correct endpoint and params
        call_args = mock_request.call_args
        assert call_args[0][1] == '/lookuptable.php'
        assert call_args[1]['params']['l'] == 4328
        assert call_args[1]['params']['s'] == '2025-2026'

        assert len(standings) == 1
        assert standings[0]['strTeam'] == 'Arsenal'
        assert standings[0]['source'] == 'thesportsdb'

    @pytest.mark.asyncio
    async def test_get_league_standings_no_results(self, client: TheSportsDBClient) -> None:
        """Test get_league_standings() handles no standings."""
        mock_response = {'table': None}

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)):
            standings = await client.get_league_standings(4328, '2025-2026')

        assert standings == []

    @pytest.mark.asyncio
    async def test_get_live_scores(self, client: TheSportsDBClient) -> None:
        """Test get_live_scores() fetches live scores."""
        mock_response = {
            'events': [
                {
                    'idEvent': '123456',
                    'strHomeTeam': 'Arsenal',
                    'strAwayTeam': 'Chelsea',
                    'intHomeScore': '2',
                    'intAwayScore': '1',
                    'strProgress': '65',
                }
            ]
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            scores = await client.get_live_scores('Soccer')

        # Verify correct endpoint and params
        call_args = mock_request.call_args
        assert call_args[0][1] == '/livescore.php'
        assert call_args[1]['params']['s'] == 'Soccer'

        assert len(scores) == 1
        assert scores[0]['source'] == 'thesportsdb'

    @pytest.mark.asyncio
    async def test_get_live_scores_no_live_games(self, client: TheSportsDBClient) -> None:
        """Test get_live_scores() handles no live games."""
        mock_response = {'events': None}

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)):
            scores = await client.get_live_scores('Soccer')

        assert scores == []

    @pytest.mark.asyncio
    async def test_search_league(self, client: TheSportsDBClient) -> None:
        """Test search_league() returns league search results."""
        mock_response = {
            'countrys': [  # API uses "countrys" instead of "leagues"
                {
                    'idLeague': '4328',
                    'strLeague': 'Premier League',
                    'strCountry': 'England',
                }
            ]
        }

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)) as mock_request:  # noqa: E501
            leagues = await client.search_league('Premier League')

        # Verify correct endpoint and params
        call_args = mock_request.call_args
        assert call_args[0][1] == '/search_all_leagues.php'
        assert call_args[1]['params']['l'] == 'Premier League'

        assert len(leagues) == 1
        assert leagues[0]['idLeague'] == '4328'
        assert leagues[0]['source'] == 'thesportsdb'

    @pytest.mark.asyncio
    async def test_search_league_no_results(self, client: TheSportsDBClient) -> None:
        """Test search_league() handles no results."""
        mock_response = {'countrys': None}

        with patch.object(client, '_request', new=AsyncMock(return_value=mock_response)):
            leagues = await client.search_league('NonexistentLeague')

        assert leagues == []

    def test_league_ids_constants(self) -> None:
        """Test LEAGUE_IDS constants are available."""
        assert LEAGUE_IDS['PREMIER_LEAGUE'] == 4328
        assert LEAGUE_IDS['LA_LIGA'] == 4335
        assert LEAGUE_IDS['BUNDESLIGA'] == 4331
        assert LEAGUE_IDS['CHAMPIONS_LEAGUE'] == 4480
        assert LEAGUE_IDS['NBA'] == 4387

    @pytest.mark.asyncio
    async def test_close_session(self, client: TheSportsDBClient) -> None:
        """Test session cleanup."""
        # Get session to create it
        await client._get_session()
        assert client._session is not None

        # Close session
        await client.close()
        assert client._session.closed
