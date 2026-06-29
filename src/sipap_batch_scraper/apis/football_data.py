"""
Football-Data.org API client.

Provides match fixtures, standings, team data for 12 major competitions.

Free tier: 10 requests/minute
Coverage: World Cup, Premier League, Champions League, Bundesliga, La Liga,
          Serie A, Ligue 1, Eredivisie, Primeira Liga, Championship, European Championship

API Documentation: https://www.football-data.org/documentation/quickstart
"""

from datetime import datetime
from typing import Any

from sipap_batch_scraper.apis.base import BaseAPIClient


class FootballDataAPI(BaseAPIClient):
    """
    Client for Football-Data.org API.

    Provides:
    - Match fixtures (upcoming, today, specific date)
    - Live scores and results
    - Team statistics and standings
    - Head-to-head history
    - Competition information

    Usage:
        api = FootballDataAPI(api_key="your-key")
        matches = await api.get_today_matches()
        standings = await api.get_standings(competition_id="PL")
        await api.close()
    """

    def __init__(self, api_key: str, timeout: int = 30) -> None:
        """
        Initialize Football-Data.org API client.

        Args:
            api_key: API authentication key from football-data.org
            timeout: Request timeout in seconds
        """
        super().__init__(
            base_url="https://api.football-data.org/v4",
            api_key=api_key,
            timeout=timeout,
        )

    def _get_default_headers(self) -> dict[str, str]:
        """Get headers for Football-Data.org API."""
        return {
            'X-Auth-Token': self.api_key,
            'Accept': 'application/json',
        }

    async def get_competitions(self) -> list[dict[str, Any]]:
        """
        Get available competitions.

        Returns:
            List of competition dictionaries with:
                - id: Competition ID (e.g., "PL", "CL", "WC")
                - name: Competition name (e.g., "Premier League")
                - area: Geographic area
                - currentSeason: Current season information
        """
        response = await self._request('GET', '/competitions')
        competitions = response.get('competitions', [])

        # Add metadata
        return [
            self._add_metadata(comp, 'football-data.org')
            for comp in competitions
        ]

    async def get_today_matches(self) -> list[dict[str, Any]]:
        """
        Get today's matches across all competitions.

        Returns:
            List of match dictionaries with:
                - id: Match ID
                - homeTeam: Home team name and ID
                - awayTeam: Away team name and ID
                - utcDate: Match date and time (ISO 8601)
                - status: Match status (SCHEDULED, IN_PLAY, FINISHED)
                - score: Match score (if available)
                - competition: Competition name
        """
        today = datetime.now().strftime('%Y-%m-%d')
        return await self.get_matches(date_from=today, date_to=today)

    async def get_matches(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        competition_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get matches with filters.

        Args:
            date_from: Start date (YYYY-MM-DD format)
            date_to: End date (YYYY-MM-DD format)
            competition_id: Filter by competition (e.g., "PL", "CL")
            status: Filter by status (SCHEDULED, IN_PLAY, FINISHED)

        Returns:
            List of match dictionaries
        """
        params: dict[str, Any] = {}
        if date_from:
            params['dateFrom'] = date_from
        if date_to:
            params['dateTo'] = date_to
        if status:
            params['status'] = status

        # Use competition-specific endpoint if provided
        if competition_id:
            endpoint = f'/competitions/{competition_id}/matches'
        else:
            endpoint = '/matches'

        response = await self._request('GET', endpoint, params=params)
        matches = response.get('matches', [])

        # Transform to SIPAP format
        return [self._transform_match(match) for match in matches]

    async def get_match(self, match_id: int) -> dict[str, Any]:
        """
        Get detailed match information.

        Args:
            match_id: Match ID from football-data.org

        Returns:
            Detailed match dictionary including lineups if available
        """
        response = await self._request('GET', f'/matches/{match_id}')
        return self._transform_match(response)

    async def get_standings(self, competition_id: str) -> list[dict[str, Any]]:
        """
        Get competition standings.

        Args:
            competition_id: Competition code (e.g., "PL", "CL", "BL1")

        Returns:
            List of team standings with position, points, wins, draws, losses
        """
        response = await self._request(
            'GET',
            f'/competitions/{competition_id}/standings'
        )

        standings_data = response.get('standings', [])
        if not standings_data:
            return []

        # Usually returns standings grouped by type (TOTAL, HOME, AWAY)
        # We want the TOTAL standings
        for standing in standings_data:
            if standing.get('type') == 'TOTAL':
                table = standing.get('table', [])
                return [
                    self._add_metadata(entry, 'football-data.org')
                    for entry in table
                ]

        # Fallback: return first standings table
        return [
            self._add_metadata(entry, 'football-data.org')
            for entry in standings_data[0].get('table', [])
        ]

    async def get_team(self, team_id: int) -> dict[str, Any]:
        """
        Get team information.

        Args:
            team_id: Team ID from football-data.org

        Returns:
            Team dictionary with name, founded, venue, squad, etc.
        """
        response = await self._request('GET', f'/teams/{team_id}')
        return self._add_metadata(response, 'football-data.org')

    async def get_head_to_head(
        self,
        team1_id: int,
        team2_id: int,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get head-to-head matches between two teams.

        Args:
            team1_id: First team ID
            team2_id: Second team ID
            limit: Maximum number of matches to return

        Returns:
            List of historical matches between the teams
        """
        # Football-Data.org doesn't have a direct H2H endpoint
        # We need to get matches for one team and filter for the other
        # This is a placeholder implementation
        # TODO: Implement by fetching team matches and filtering
        raise NotImplementedError(
            "H2H not yet implemented for Football-Data.org. "
            "Use match history from both teams and filter."
        )

    def _transform_match(self, match: dict[str, Any]) -> dict[str, Any]:
        """
        Transform Football-Data.org match format to SIPAP format.

        Args:
            match: Raw match data from API

        Returns:
            Transformed match dictionary
        """
        home_team = match.get('homeTeam', {})
        away_team = match.get('awayTeam', {})
        score = match.get('score', {})
        full_time = score.get('fullTime', {})

        transformed = {
            'external_id': str(match.get('id')),
            'home_team': home_team.get('name'),
            'home_team_id': home_team.get('id'),
            'away_team': away_team.get('name'),
            'away_team_id': away_team.get('id'),
            'utc_date': match.get('utcDate'),
            'status': match.get('status'),
            'competition': match.get('competition', {}).get('name'),
            'competition_id': match.get('competition', {}).get('id'),
            'season': match.get('season', {}).get('startDate'),
            'matchday': match.get('matchday'),
            'stage': match.get('stage'),
            'venue': match.get('venue'),
            'source': 'football-data.org',
        }

        # Add score if available
        if full_time.get('home') is not None:
            transformed['score_home'] = full_time.get('home')
            transformed['score_away'] = full_time.get('away')

        # Add half-time score if available
        half_time = score.get('halfTime', {})
        if half_time.get('home') is not None:
            transformed['score_half_home'] = half_time.get('home')
            transformed['score_half_away'] = half_time.get('away')

        return self._add_metadata(transformed, 'football-data.org')
