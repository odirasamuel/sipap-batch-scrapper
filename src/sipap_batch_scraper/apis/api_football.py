"""
API-Football client (PLACEHOLDER - Not yet configured).

Comprehensive football data API with live scores, detailed statistics, lineups.

Pricing: $19/mo (PRO), $29/mo (ULTRA), $39/mo (MEGA)
PRO includes: 7,500 requests/day, 300 req/min, all endpoints
Coverage: 900+ competitions, 30+ sports

API Documentation: https://www.api-football.com/documentation-v3

TODO: Get API key from https://dashboard.api-football.com/
TODO: Implement after getting subscription
"""

from typing import Any

from sipap_batch_scraper.apis.base import BaseAPIClient


class APIFootballClient(BaseAPIClient):
    """
    Client for API-Football (PLACEHOLDER).

    Features (when implemented):
    - Live scores with minute-by-minute updates
    - Detailed match statistics (possession, shots, cards, etc.)
    - Player statistics and lineups
    - Injuries and suspensions
    - Predictions and betting tips
    - H2H history with detailed stats
    - Venue information

    Status: PLACEHOLDER - Requires API key and subscription
    """

    def __init__(self, api_key: str = "NOT_CONFIGURED", timeout: int = 30) -> None:
        """
        Initialize API-Football client.

        Args:
            api_key: API key from api-football.com (currently not configured)
            timeout: Request timeout in seconds
        """
        super().__init__(
            base_url="https://v3.football.api-sports.io",
            api_key=api_key,
            timeout=timeout,
        )
        self._configured = api_key != "NOT_CONFIGURED"

    def _check_configured(self) -> None:
        """Raise error if API is not configured."""
        if not self._configured:
            raise NotImplementedError(
                "API-Football is not yet configured. "
                "Please get an API key from https://dashboard.api-football.com/ "
                "and initialize with: APIFootballClient(api_key='your-key')"
            )

    def _get_default_headers(self) -> dict[str, str]:
        """Get headers for API-Football."""
        return {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': 'v3.football.api-sports.io',
        }

    async def get_today_matches(self) -> list[dict[str, Any]]:
        """Get today's matches (PLACEHOLDER)."""
        self._check_configured()
        # Implementation after getting API key
        raise NotImplementedError("Pending API key configuration")

    async def get_match_statistics(self, fixture_id: int) -> dict[str, Any]:
        """Get detailed match statistics (PLACEHOLDER)."""
        self._check_configured()
        raise NotImplementedError("Pending API key configuration")

    async def get_lineups(self, fixture_id: int) -> dict[str, Any]:
        """Get team lineups for a match (PLACEHOLDER)."""
        self._check_configured()
        raise NotImplementedError("Pending API key configuration")

    async def get_player_statistics(
        self,
        fixture_id: int,
    ) -> list[dict[str, Any]]:
        """Get player statistics for a match (PLACEHOLDER)."""
        self._check_configured()
        raise NotImplementedError("Pending API key configuration")

    async def get_injuries(self, team_id: int) -> list[dict[str, Any]]:
        """Get team injury list (PLACEHOLDER)."""
        self._check_configured()
        raise NotImplementedError("Pending API key configuration")

    async def get_h2h(
        self,
        team1_id: int,
        team2_id: int,
    ) -> list[dict[str, Any]]:
        """Get head-to-head matches with detailed stats (PLACEHOLDER)."""
        self._check_configured()
        raise NotImplementedError("Pending API key configuration")


# Placeholder for future use
__all__ = ['APIFootballClient']
