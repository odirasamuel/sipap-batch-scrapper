"""
The Odds API client.

Provides betting odds from bookmakers worldwide.

Free tier: 500 credits/month (~16 requests/day)
Coverage: 40+ sports, 80+ bookmakers
Features: Live odds, odds movements, market comparison

API Documentation: https://the-odds-api.com/liveapi/guides/v4/
"""

from typing import Any

from sipap_batch_scraper.apis.base import BaseAPIClient


class OddsAPI(BaseAPIClient):
    """
    Client for The Odds API.

    Provides:
    - Live odds from 80+ bookmakers
    - Odds movements and history
    - Market comparison (best odds)
    - Multiple bet types (h2h, spreads, totals)
    - Arbitrage opportunities

    Usage:
        api = OddsAPI(api_key="your-key")
        odds = await api.get_odds(sport="soccer_epl")
        event_odds = await api.get_event_odds(event_id="abc123")
        await api.close()
    """

    def __init__(self, api_key: str, timeout: int = 30) -> None:
        """
        Initialize The Odds API client.

        Args:
            api_key: API authentication key from the-odds-api.com
            timeout: Request timeout in seconds
        """
        super().__init__(
            base_url="https://api.the-odds-api.com/v4",
            api_key=api_key,
            timeout=timeout,
        )

    async def get_sports(self) -> list[dict[str, Any]]:
        """
        Get available sports.

        Returns:
            List of sport dictionaries with:
                - key: Sport identifier (e.g., "soccer_epl", "soccer_uefa_champs_league")
                - group: Sport group (e.g., "Soccer", "Basketball")
                - title: Human-readable title
                - description: Sport description
                - active: Whether sport has active events
                - has_outrights: Whether sport has outright markets
        """
        params = {'apiKey': self.api_key}
        response = await self._request('GET', '/sports', params=params)

        # Response is a list in this case, not a dict
        sports_list: list[Any] = response  # type: ignore[assignment]
        return [
            self._add_metadata(sport, 'the-odds-api')
            for sport in sports_list
        ]

    async def get_odds(
        self,
        sport: str,
        regions: str = 'uk,us,eu',
        markets: str = 'h2h',
        odds_format: str = 'decimal',
        date_format: str = 'iso',
    ) -> list[dict[str, Any]]:
        """
        Get odds for all events in a sport.

        Args:
            sport: Sport key (e.g., "soccer_epl", "soccer_uefa_champs_league")
            regions: Bookmaker regions (comma-separated: uk, us, eu, au)
            markets: Bet types (h2h=moneyline, spreads, totals, outrights)
            odds_format: decimal, american, or fractional
            date_format: iso or unix

        Returns:
            List of event dictionaries with odds from multiple bookmakers
        """
        params = {
            'apiKey': self.api_key,
            'regions': regions,
            'markets': markets,
            'oddsFormat': odds_format,
            'dateFormat': date_format,
        }

        endpoint = f'/sports/{sport}/odds'
        response = await self._request('GET', endpoint, params=params)

        # Response is a list of events
        events_list: list[Any] = response  # type: ignore[assignment]
        return [self._transform_odds(event) for event in events_list]

    async def get_event_odds(
        self,
        sport: str,
        event_id: str,
        regions: str = 'uk,us,eu',
        markets: str = 'h2h',
        odds_format: str = 'decimal',
        date_format: str = 'iso',
    ) -> dict[str, Any]:
        """
        Get odds for a specific event.

        Args:
            sport: Sport key
            event_id: Event ID from The Odds API
            regions: Bookmaker regions
            markets: Bet types
            odds_format: decimal, american, or fractional
            date_format: iso or unix

        Returns:
            Event dictionary with detailed odds from all bookmakers
        """
        params = {
            'apiKey': self.api_key,
            'regions': regions,
            'markets': markets,
            'oddsFormat': odds_format,
            'dateFormat': date_format,
        }

        endpoint = f'/sports/{sport}/events/{event_id}/odds'
        response = await self._request('GET', endpoint, params=params)

        return self._transform_odds(response)

    async def get_scores(
        self,
        sport: str,
        days_from: int = 1,
        date_format: str = 'iso',
    ) -> list[dict[str, Any]]:
        """
        Get recent and live scores.

        Args:
            sport: Sport key
            days_from: Number of days from today (1-3, negative for past)
            date_format: iso or unix

        Returns:
            List of events with scores
        """
        params = {
            'apiKey': self.api_key,
            'daysFrom': days_from,
            'dateFormat': date_format,
        }

        endpoint = f'/sports/{sport}/scores'
        response = await self._request('GET', endpoint, params=params)

        # Response is a list of events
        events_list: list[Any] = response  # type: ignore[assignment]
        return [
            self._add_metadata(event, 'the-odds-api')
            for event in events_list
        ]

    async def get_usage(self) -> dict[str, Any]:
        """
        Get API usage statistics.

        Returns:
            Dictionary with:
                - used: Credits used this month
                - remaining: Credits remaining
                - reset_date: When credits reset
        """
        # The Odds API returns usage in response headers (X-Requests-Used, X-Requests-Remaining)
        # For now, return a placeholder
        # TODO: Capture usage from response headers
        return {
            'message': 'Usage tracking requires checking response headers',
            'source': 'the-odds-api',
        }

    def _transform_odds(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Transform The Odds API format to SIPAP format.

        Args:
            event: Raw event data from API

        Returns:
            Transformed odds dictionary
        """
        bookmakers = event.get('bookmakers', [])

        # Extract best odds across all bookmakers
        best_home = 0.0
        best_draw = 0.0
        best_away = 0.0

        for bookmaker in bookmakers:
            markets = bookmaker.get('markets', [])
            for market in markets:
                if market.get('key') == 'h2h':
                    outcomes = market.get('outcomes', [])
                    for outcome in outcomes:
                        name = outcome.get('name')
                        price = outcome.get('price', 0.0)

                        # Match home team
                        if name == event.get('home_team'):
                            best_home = max(best_home, price)
                        # Match away team
                        elif name == event.get('away_team'):
                            best_away = max(best_away, price)
                        # Draw
                        elif name == 'Draw':
                            best_draw = max(best_draw, price)

        transformed = {
            'external_id': event.get('id'),
            'sport_key': event.get('sport_key'),
            'sport_title': event.get('sport_title'),
            'commence_time': event.get('commence_time'),
            'home_team': event.get('home_team'),
            'away_team': event.get('away_team'),
            'bookmakers': bookmakers,  # Keep raw bookmaker data
            'best_odds': {
                'home': best_home,
                'draw': best_draw if best_draw > 0 else None,
                'away': best_away,
            },
            'num_bookmakers': len(bookmakers),
        }

        return self._add_metadata(transformed, 'the-odds-api')


# Common sport keys for easy reference
SPORT_KEYS = {
    # Soccer
    'PREMIER_LEAGUE': 'soccer_epl',
    'CHAMPIONS_LEAGUE': 'soccer_uefa_champs_league',
    'EUROPA_LEAGUE': 'soccer_uefa_europa_league',
    'LA_LIGA': 'soccer_spain_la_liga',
    'BUNDESLIGA': 'soccer_germany_bundesliga',
    'SERIE_A': 'soccer_italy_serie_a',
    'LIGUE_1': 'soccer_france_ligue_one',
    'WORLD_CUP': 'soccer_fifa_world_cup',
    'EUROS': 'soccer_uefa_european_championship',

    # Other sports (for future expansion)
    'NBA': 'basketball_nba',
    'NFL': 'americanfootball_nfl',
    'MLB': 'baseball_mlb',
    'NHL': 'icehockey_nhl',
}
