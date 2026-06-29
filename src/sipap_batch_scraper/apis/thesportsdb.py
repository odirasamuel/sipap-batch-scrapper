"""
TheSportsDB API client.

Sports data API with live scores, events, teams, players across 40+ sports.

Pricing:
- Free: $0/mo (30 req/min, limited data, read-only)
- Single Developer: $9/mo (2-min livescore delay, 100 req/min)
- Small Business: $20/mo (no data limits, 120 req/min)

Coverage: 40+ sports including Soccer, NFL, NBA, MLB, NHL
Features: Team info, player stats, events, league standings, highlights

API Documentation: https://www.thesportsdb.com/api.php
Example: https://www.thesportsdb.com/api/v1/json/123/searchteams.php?t=Arsenal
"""

from typing import Any

from sipap_batch_scraper.apis.base import BaseAPIClient


class TheSportsDBClient(BaseAPIClient):
    """
    Client for TheSportsDB API.

    Features:
    - Team and player information
    - Event schedules and results
    - League standings
    - Sport highlights and videos
    - Multi-sport coverage
    - Live scores (paid tiers only)

    Free Tier Limitations:
    - 30 requests/minute
    - Read-only access
    - Limited data compared to paid tiers
    - No real-time live scores (paid feature)

    Usage:
        client = TheSportsDBClient(api_key="123")
        teams = await client.search_team("Arsenal")
        events = await client.get_events_next_league(4328)  # Premier League
        standings = await client.get_league_standings(4328, "2025-2026")
        await client.close()
    """

    def __init__(self, api_key: str = "123", timeout: int = 30) -> None:
        """
        Initialize TheSportsDB client.

        Args:
            api_key: API key from thesportsdb.com (default: "123" free tier)
            timeout: Request timeout in seconds
        """
        # Base URL includes API key in path
        super().__init__(
            base_url=f"https://www.thesportsdb.com/api/v1/json/{api_key}",
            api_key=api_key,
            timeout=timeout,
        )

    async def search_team(self, team_name: str) -> list[dict[str, Any]]:
        """
        Search for teams by name.

        Args:
            team_name: Team name to search for (e.g., "Arsenal", "Barcelona")

        Returns:
            List of team dictionaries with:
                - idTeam: Team ID
                - strTeam: Team name
                - strLeague: League name
                - strStadium: Stadium name
                - intFormedYear: Year founded
                - strCountry: Country
                - strBadge: Team badge URL
                - strDescription: Team description

        Example:
            teams = await client.search_team("Arsenal")
        """
        response = await self._request('GET', '/searchteams.php', params={'t': team_name})
        teams = response.get('teams') or []

        return [
            self._add_metadata(team, 'thesportsdb')
            for team in teams
        ]

    async def get_team(self, team_id: int) -> dict[str, Any]:
        """
        Get detailed team information by ID.

        Args:
            team_id: Team ID from TheSportsDB

        Returns:
            Team dictionary with full details including squad, social media, etc.

        Example:
            team = await client.get_team(133604)  # Arsenal
        """
        response = await self._request('GET', '/lookupteam.php', params={'id': team_id})
        teams = response.get('teams') or []

        if not teams:
            return {}

        return self._add_metadata(teams[0], 'thesportsdb')

    async def search_player(self, player_name: str) -> list[dict[str, Any]]:
        """
        Search for players by name.

        Args:
            player_name: Player name to search for (e.g., "Messi", "Ronaldo")

        Returns:
            List of player dictionaries

        Example:
            players = await client.search_player("Messi")
        """
        response = await self._request('GET', '/searchplayers.php', params={'p': player_name})
        players = response.get('player') or []

        return [
            self._add_metadata(player, 'thesportsdb')
            for player in players
        ]

    async def get_player(self, player_id: int) -> dict[str, Any]:
        """
        Get detailed player information by ID.

        Args:
            player_id: Player ID from TheSportsDB

        Returns:
            Player dictionary with full details

        Example:
            player = await client.get_player(34145937)
        """
        response = await self._request('GET', '/lookupplayer.php', params={'id': player_id})
        players = response.get('players') or []

        if not players:
            return {}

        return self._add_metadata(players[0], 'thesportsdb')

    async def get_events_next_league(self, league_id: int) -> list[dict[str, Any]]:
        """
        Get next 15 events for a league.

        Args:
            league_id: League ID from TheSportsDB (e.g., 4328 for Premier League)

        Returns:
            List of upcoming event dictionaries

        Example:
            events = await client.get_events_next_league(4328)  # Premier League
        """
        response = await self._request('GET', '/eventsnextleague.php', params={'id': league_id})
        events = response.get('events') or []

        return [
            self._add_metadata(event, 'thesportsdb')
            for event in events
        ]

    async def get_events(
        self,
        league_id: int,
        season: str,
    ) -> list[dict[str, Any]]:
        """
        Get events for a league season.

        Args:
            league_id: League ID from TheSportsDB
            season: Season string (e.g., "2025-2026")

        Returns:
            List of event dictionaries for the season

        Example:
            events = await client.get_events(4328, "2025-2026")
        """
        response = await self._request(
            'GET',
            '/eventsseason.php',
            params={'id': league_id, 's': season}
        )
        events = response.get('events') or []

        return [
            self._add_metadata(event, 'thesportsdb')
            for event in events
        ]

    async def get_league_standings(
        self,
        league_id: int,
        season: str,
    ) -> list[dict[str, Any]]:
        """
        Get league standings for a season.

        Args:
            league_id: League ID from TheSportsDB
            season: Season string (e.g., "2025-2026")

        Returns:
            List of team standings with position, points, wins, draws, losses

        Example:
            standings = await client.get_league_standings(4328, "2025-2026")
        """
        response = await self._request(
            'GET',
            '/lookuptable.php',
            params={'l': league_id, 's': season}
        )
        standings = response.get('table') or []

        return [
            self._add_metadata(entry, 'thesportsdb')
            for entry in standings
        ]

    async def get_live_scores(self, sport: str = "Soccer") -> list[dict[str, Any]]:
        """
        Get live scores for a sport.

        Note: This endpoint is available on free tier but with delayed data.
        Real-time scores require paid subscription.

        Args:
            sport: Sport name (e.g., "Soccer", "Basketball", "Football")

        Returns:
            List of live event dictionaries (may be empty on free tier)

        Example:
            scores = await client.get_live_scores("Soccer")
        """
        response = await self._request('GET', '/livescore.php', params={'s': sport})
        events = response.get('events') or []

        return [
            self._add_metadata(event, 'thesportsdb')
            for event in events
        ]

    async def search_league(self, league_name: str) -> list[dict[str, Any]]:
        """
        Search for leagues by name.

        Args:
            league_name: League name to search for (e.g., "Premier League")

        Returns:
            List of league dictionaries

        Example:
            leagues = await client.search_league("Premier League")
        """
        response = await self._request('GET', '/search_all_leagues.php', params={'l': league_name})
        leagues_data = response.get('countrys') or []  # API typo: "countrys" instead of "leagues"

        return [
            self._add_metadata(league, 'thesportsdb')
            for league in leagues_data
        ]


# Common league IDs for easy reference
LEAGUE_IDS = {
    # Soccer
    'PREMIER_LEAGUE': 4328,
    'LA_LIGA': 4335,
    'BUNDESLIGA': 4331,
    'SERIE_A': 4332,
    'LIGUE_1': 4334,
    'CHAMPIONS_LEAGUE': 4480,
    'EUROPA_LEAGUE': 4481,
    'WORLD_CUP': 4429,
    'EUROS': 4764,

    # Other sports
    'NBA': 4387,
    'NFL': 4391,
    'MLB': 4424,
    'NHL': 4380,
}


__all__ = ['TheSportsDBClient', 'LEAGUE_IDS']
