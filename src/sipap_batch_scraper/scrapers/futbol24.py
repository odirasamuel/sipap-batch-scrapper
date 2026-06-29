"""
Futbol24 scraper for match data.

Extracts match schedules, live scores, and historical data from Futbol24.
Futbol24 provides comprehensive current and historical football data.
"""

from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup

from sipap_batch_scraper.scrapers.base import BaseScraper


class Futbol24Scraper:
    """
    Scraper for Futbol24 match data.

    Futbol24 provides:
    - Current match schedules and live scores
    - Historical match data (past results)
    - More data depth than FlashScore for trend analysis
    - All FlashScore features except player stats and news

    Phase 1: Match Discovery
    - Extracts basic match data: teams, time, league, status, score

    Future phases will add:
    - Historical statistics and trends
    - Detailed H2H analysis
    - Long-term pattern analysis

    Usage:
        scraper = Futbol24Scraper(timeout=30000)
        matches = await scraper.scrape_today_matches()
        historical = await scraper.scrape_matches(date="2026-05-15")
    """

    def __init__(self, timeout: int = 15000) -> None:
        """
        Initialize Futbol24 scraper.

        Args:
            timeout: Page load timeout in milliseconds (default: 15000)
        """
        self.base_url = "https://www.futbol24.com"
        self.timeout = timeout
        self.base_scraper = BaseScraper(timeout=timeout)

    def _get_football_url(self, date: str | None = None) -> str:
        """
        Construct Futbol24 football URL.

        Args:
            date: Optional date string in YYYY-MM-DD format

        Returns:
            Full URL for football matches
        """
        if date:
            # Futbol24 uses date in URL path or query parameter
            return f"{self.base_url}/live/?date={date}"
        return f"{self.base_url}/live/"

    def _parse_matches(self, html: str) -> list[dict[str, Any]]:
        """
        Parse match data from Futbol24 HTML.

        Extracts structured match data using BeautifulSoup CSS selectors.

        Args:
            html: Raw HTML content from Futbol24

        Returns:
            List of match dictionaries with fields:
                - home_team: Name of home team
                - away_team: Name of away team
                - time: Match time or minute if live (e.g., '18:00' or '72'')
                - league: Competition name
                - status: 'scheduled', 'live', or 'finished'
                - score: Match score (only for live/finished matches)
                - match_date: Date of match (for historical matches)
                - external_id: Futbol24 match ID (if available)
                - source: Always 'futbol24'
                - scraped_at: ISO 8601 timestamp

        Note:
            Skips matches with missing required data (home_team, away_team).
            Gracefully handles incomplete HTML elements.
        """
        soup = BeautifulSoup(html, 'lxml')
        matches: list[dict[str, Any]] = []
        scraped_at = datetime.now(UTC).isoformat()

        # Find all match elements
        # Futbol24 uses class="match" for match containers
        match_elements = soup.find_all('div', class_='match')

        for match_elem in match_elements:
            try:
                # Extract home and away teams
                home_elem = match_elem.find('div', class_='team-home')
                away_elem = match_elem.find('div', class_='team-away')

                # Skip matches missing required data
                if not home_elem or not away_elem:
                    continue

                home_team = home_elem.get_text(strip=True)
                away_team = away_elem.get_text(strip=True)

                # Extract time
                time_elem = match_elem.find('div', class_='match-time')
                time = time_elem.get_text(strip=True) if time_elem else None

                # Extract league/competition
                league_elem = match_elem.find('div', class_='competition')
                league = league_elem.get_text(strip=True) if league_elem else None

                # Determine match status
                status = 'scheduled'
                score = None

                # Check for live matches
                if 'live' in match_elem.get('class', []):
                    status = 'live'
                    score_elem = match_elem.find('div', class_='score')
                    if score_elem:
                        score = score_elem.get_text(strip=True)
                # Check for finished matches
                elif 'finished' in match_elem.get('class', []):
                    status = 'finished'
                    score_elem = match_elem.find('div', class_='score')
                    if score_elem:
                        score = score_elem.get_text(strip=True)

                # Extract match ID if present
                match_id = match_elem.get('data-match-id', '')
                external_id = match_id if match_id else None

                # Extract match date (for historical matches)
                date_elem = match_elem.find('div', class_='match-date')
                match_date = date_elem.get_text(strip=True) if date_elem else None

                # Build match dictionary
                match = {
                    'home_team': home_team,
                    'away_team': away_team,
                    'time': time,
                    'league': league,
                    'status': status,
                    'source': 'futbol24',
                    'scraped_at': scraped_at,
                }

                # Add optional fields if present
                if score:
                    match['score'] = score
                if external_id:
                    match['external_id'] = external_id
                if match_date:
                    match['match_date'] = match_date

                matches.append(match)

            except Exception:
                # Skip malformed match elements
                continue

        return matches

    async def scrape_today_matches(self) -> list[dict[str, Any]]:
        """
        Scrape today's matches from Futbol24.

        Returns:
            List of match dictionaries for today

        Raises:
            Exception: If network request fails
        """
        url = self._get_football_url()
        html = await self.base_scraper.scrape(url)
        return self._parse_matches(html)

    async def scrape_matches(self, date: str) -> list[dict[str, Any]]:
        """
        Scrape matches for a specific date.

        Args:
            date: Date string in YYYY-MM-DD format

        Returns:
            List of match dictionaries for specified date

        Raises:
            Exception: If network request fails

        Note:
            Futbol24's strength is historical data - use this method
            to scrape past matches for trend analysis.
        """
        url = self._get_football_url(date=date)
        html = await self.base_scraper.scrape(url)
        return self._parse_matches(html)

    def _get_h2h_url(self, team1: str, team2: str) -> str:
        """
        Construct Futbol24 head-to-head URL.

        Args:
            team1: First team name/slug
            team2: Second team name/slug

        Returns:
            Full URL for H2H history
        """
        return f"{self.base_url}/h2h/{team1}-vs-{team2}/"

    def _get_trends_url(self, team: str) -> str:
        """
        Construct Futbol24 team trends URL.

        Args:
            team: Team name/slug

        Returns:
            Full URL for team trends
        """
        return f"{self.base_url}/team/{team}/trends/"

    def _parse_h2h(self, html: str) -> list[dict[str, Any]]:
        """
        Parse head-to-head history from Futbol24 HTML.

        Args:
            html: Raw HTML content from Futbol24 H2H page

        Returns:
            List of H2H match dictionaries
        """
        from bs4 import Tag

        soup = BeautifulSoup(html, 'lxml')
        h2h_matches: list[dict[str, Any]] = []

        # Find H2H container
        h2h_container = soup.find('div', class_='h2h-container')
        if not h2h_container or not isinstance(h2h_container, Tag):
            return h2h_matches

        # Find individual H2H matches
        match_elements = h2h_container.find_all('div', class_='h2h-match')

        for match_elem in match_elements:
            if not isinstance(match_elem, Tag):
                continue

            try:
                date_elem = match_elem.find('span', class_='h2h-date')
                home_elem = match_elem.find('span', class_='h2h-home')
                score_elem = match_elem.find('span', class_='h2h-score')
                away_elem = match_elem.find('span', class_='h2h-away')

                if not all([date_elem, home_elem, score_elem, away_elem]):
                    continue

                if not (isinstance(date_elem, Tag) and isinstance(home_elem, Tag) and
                        isinstance(score_elem, Tag) and isinstance(away_elem, Tag)):
                    continue

                h2h_matches.append({
                    'date': date_elem.get_text(strip=True),
                    'home_team': home_elem.get_text(strip=True),
                    'score': score_elem.get_text(strip=True),
                    'away_team': away_elem.get_text(strip=True),
                    'source': 'futbol24',
                })
            except AttributeError:
                continue

        return h2h_matches

    def _parse_trends(self, html: str) -> dict[str, Any]:
        """
        Parse team trends from Futbol24 HTML.

        Args:
            html: Raw HTML content from Futbol24 trends page

        Returns:
            Dictionary with trend statistics
        """
        from bs4 import Tag

        soup = BeautifulSoup(html, 'lxml')
        trends: dict[str, Any] = {'scraped_at': datetime.now(UTC).isoformat()}

        # Find trends container
        trends_container = soup.find('div', class_='trends-container')
        if not trends_container or not isinstance(trends_container, Tag):
            return trends

        # Find individual trend stats
        trend_stats = trends_container.find_all('div', class_='trend-stat')

        for stat_elem in trend_stats:
            if not isinstance(stat_elem, Tag):
                continue

            try:
                label_elem = stat_elem.find('span', class_='stat-label')
                value_elem = stat_elem.find('span', class_='stat-value')

                if not (label_elem and value_elem and isinstance(label_elem, Tag) and
                        isinstance(value_elem, Tag)):
                    continue

                label = label_elem.get_text(strip=True).lower()
                value = value_elem.get_text(strip=True)

                # Map labels to dictionary keys
                if 'last 5' in label:
                    trends['last_5_matches'] = value
                elif 'goals scored' in label:
                    try:
                        trends['goals_scored_avg'] = float(value)
                    except ValueError:
                        trends['goals_scored_avg'] = value
                elif 'goals conceded' in label:
                    try:
                        trends['goals_conceded_avg'] = float(value)
                    except ValueError:
                        trends['goals_conceded_avg'] = value
                else:
                    # Store other stats with cleaned key
                    key = label.replace(' ', '_').replace('(', '').replace(')', '')
                    trends[key] = value

            except AttributeError:
                continue

        return trends

    async def scrape_h2h(self, team1: str, team2: str) -> list[dict[str, Any]]:
        """
        Scrape head-to-head history for two teams.

        Args:
            team1: First team name/slug
            team2: Second team name/slug

        Returns:
            List of H2H match dictionaries

        Raises:
            Exception: If network request fails

        Note:
            Futbol24's unique value is historical depth - use this method
            for long-term H2H analysis and pattern discovery.
        """
        url = self._get_h2h_url(team1, team2)
        html = await self.base_scraper.scrape(url)
        return self._parse_h2h(html)

    async def scrape_trends(self, team: str) -> dict[str, Any]:
        """
        Scrape team trends and statistics.

        Args:
            team: Team name/slug

        Returns:
            Dictionary with trend statistics

        Raises:
            Exception: If network request fails

        Note:
            Trends include last 5 matches form, average goals scored/conceded,
            and other statistical patterns useful for prediction.
        """
        url = self._get_trends_url(team)
        html = await self.base_scraper.scrape(url)
        return self._parse_trends(html)
