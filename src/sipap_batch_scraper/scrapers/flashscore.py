"""
FlashScore scraper for match schedules, live scores, and team stats.

Scrapes football match data from flashscore.com using Playwright + BeautifulSoup.
"""

from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup

from .base import BaseScraper


class FlashScoreScraper:
    """
    FlashScore scraper for football match data.

    Features:
    - Match schedule scraping (today or specific date)
    - Live score extraction
    - Team statistics
    - Anti-detection via BaseScraper
    - Structured data output

    Example:
        >>> scraper = FlashScoreScraper()
        >>> matches = await scraper.scrape_today_matches()
        >>> print(len(matches))
        20
        >>> print(matches[0]['home_team'])
        'Arsenal'
    """

    def __init__(self, timeout: int = 15000) -> None:
        """
        Initialize FlashScore scraper.

        Args:
            timeout: Page load timeout in milliseconds (default: 15000ms = 15s)
        """
        self.base_url = "https://www.flashscore.com"
        self.timeout = timeout
        self.base_scraper = BaseScraper(timeout=timeout)

    def _get_football_url(self, date: str | None = None) -> str:
        """
        Construct FlashScore football URL.

        Args:
            date: Optional date in YYYY-MM-DD format

        Returns:
            Full URL for football section
        """
        url = f"{self.base_url}/football/"

        if date:
            # FlashScore uses date parameter for filtering
            url = f"{url}?date={date}"

        return url

    def _parse_matches(self, html: str) -> list[dict[str, Any]]:
        """
        Parse match data from HTML.

        Args:
            html: Raw HTML content from FlashScore

        Returns:
            List of match dictionaries with structured data

        Example match dict:
            {
                'home_team': 'Arsenal',
                'away_team': 'Chelsea',
                'time': '15:00',
                'league': 'Premier League',
                'status': 'scheduled',  # or 'live', 'finished'
                'score': '2 - 1',  # if live/finished
                'external_id': 'ABC123',  # match ID from FlashScore
                'source': 'flashscore',
                'scraped_at': '2026-06-27T14:30:00Z'
            }
        """
        soup = BeautifulSoup(html, 'lxml')
        matches: list[dict[str, Any]] = []
        scraped_at = datetime.now(UTC).isoformat()

        # Find all match containers
        match_elements = soup.find_all('div', class_='event__match')

        for match_elem in match_elements:
            try:
                # Extract teams
                home_elem = match_elem.find('div', class_='event__participant--home')
                away_elem = match_elem.find('div', class_='event__participant--away')

                # Skip if required data is missing
                if not home_elem or not away_elem:
                    continue

                home_team = home_elem.get_text(strip=True)
                away_team = away_elem.get_text(strip=True)

                # Extract time/status
                time_elem = match_elem.find('div', class_='event__time')
                time = time_elem.get_text(strip=True) if time_elem else None

                # Extract league
                league_elem = match_elem.find('div', class_='event__stage')
                league = league_elem.get_text(strip=True) if league_elem else None

                # Determine status (live, scheduled, finished)
                status = 'scheduled'
                score = None

                if 'event__match--live' in match_elem.get('class', []):
                    status = 'live'
                    # Extract score for live matches
                    score_elem = match_elem.find('div', class_='event__score')
                    if score_elem:
                        score = score_elem.get_text(strip=True)

                # Extract match ID if available
                match_id = match_elem.get('id', '')
                # FlashScore IDs often look like "g_1_ABC123"
                external_id = match_id.replace('g_1_', '') if match_id else None

                # Build match dictionary
                match = {
                    'home_team': home_team,
                    'away_team': away_team,
                    'time': time,
                    'league': league,
                    'status': status,
                    'source': 'flashscore',
                    'scraped_at': scraped_at,
                }

                # Add optional fields
                if score:
                    match['score'] = score
                if external_id:
                    match['external_id'] = external_id

                matches.append(match)

            except Exception:
                # Skip matches with parsing errors
                # Log error in production (not implemented yet)
                continue

        return matches

    async def scrape_today_matches(self) -> list[dict[str, Any]]:
        """
        Scrape today's football matches.

        Returns:
            List of match dictionaries

        Raises:
            Exception: If scraping fails

        Example:
            >>> scraper = FlashScoreScraper()
            >>> matches = await scraper.scrape_today_matches()
            >>> print(f"Found {len(matches)} matches today")
            Found 25 matches today
        """
        url = self._get_football_url()
        html = await self.base_scraper.scrape(url)
        return self._parse_matches(html)

    async def scrape_matches(self, date: str) -> list[dict[str, Any]]:
        """
        Scrape matches for a specific date.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            List of match dictionaries

        Raises:
            Exception: If scraping fails

        Example:
            >>> scraper = FlashScoreScraper()
            >>> matches = await scraper.scrape_matches("2026-06-28")
            >>> print(f"Found {len(matches)} matches on 2026-06-28")
            Found 30 matches on 2026-06-28
        """
        url = self._get_football_url(date=date)
        html = await self.base_scraper.scrape(url)
        return self._parse_matches(html)

    def _get_match_url(self, match_id: str) -> str:
        """
        Construct FlashScore match-specific URL.

        Args:
            match_id: FlashScore match identifier

        Returns:
            Full URL for specific match details
        """
        return f"{self.base_url}/match/{match_id}/"

    def _parse_odds(self, html: str) -> dict[str, Any] | None:
        """
        Parse match odds from FlashScore HTML.

        Args:
            html: Raw HTML content from FlashScore match page

        Returns:
            Odds dictionary with home/draw/away odds, or None if not found

        Note:
            Adds source and scraped_at fields automatically.
        """
        from bs4 import Tag

        soup = BeautifulSoup(html, 'lxml')
        scraped_at = datetime.now(UTC).isoformat()

        # Find odds section
        odds_section = soup.find('div', class_='odds-section')
        if not odds_section or not isinstance(odds_section, Tag):
            return None

        try:
            home_elem = odds_section.find('div', class_='odd-home')
            draw_elem = odds_section.find('div', class_='odd-draw')
            away_elem = odds_section.find('div', class_='odd-away')

            if not (home_elem and draw_elem and away_elem):
                return None

            # Type guard: ensure elements are Tags
            if not (isinstance(home_elem, Tag) and isinstance(draw_elem, Tag) and
                    isinstance(away_elem, Tag)):
                return None

            return {
                'home': float(home_elem.get_text(strip=True)),
                'draw': float(draw_elem.get_text(strip=True)),
                'away': float(away_elem.get_text(strip=True)),
                'source': 'flashscore',
                'scraped_at': scraped_at,
            }
        except (ValueError, AttributeError):
            return None

    def _parse_lineups(self, html: str) -> dict[str, list[str]]:
        """
        Parse team lineups from FlashScore HTML.

        Args:
            html: Raw HTML content from FlashScore match page

        Returns:
            Dictionary with 'home' and 'away' player lists
        """
        from bs4 import Tag

        soup = BeautifulSoup(html, 'lxml')
        lineups: dict[str, list[str]] = {'home': [], 'away': []}

        # Find lineup sections
        home_lineup = soup.find('div', class_='lineup-home')
        away_lineup = soup.find('div', class_='lineup-away')

        if home_lineup and isinstance(home_lineup, Tag):
            players = home_lineup.find_all('div', class_='player')
            lineups['home'] = [p.get_text(strip=True) for p in players if isinstance(p, Tag)]

        if away_lineup and isinstance(away_lineup, Tag):
            players = away_lineup.find_all('div', class_='player')
            lineups['away'] = [p.get_text(strip=True) for p in players if isinstance(p, Tag)]

        return lineups

    def _parse_player_stats(self, html: str) -> list[dict[str, Any]]:
        """
        Parse player statistics from FlashScore HTML.

        Args:
            html: Raw HTML content from FlashScore match page

        Returns:
            List of player stat dictionaries
        """
        soup = BeautifulSoup(html, 'lxml')
        stats: list[dict[str, Any]] = []

        # Find player stats sections
        player_stats_sections = soup.find_all('div', class_='player-stats')

        for player_section in player_stats_sections:
            try:
                name_elem = player_section.find('div', class_='player-name')
                goals_elem = player_section.find('div', class_='goals')
                assists_elem = player_section.find('div', class_='assists')
                shots_elem = player_section.find('div', class_='shots')

                if name_elem:
                    player_stat = {
                        'name': name_elem.get_text(strip=True),
                        'goals': int(goals_elem.get_text(strip=True)) if goals_elem else 0,
                        'assists': int(assists_elem.get_text(strip=True)) if assists_elem else 0,
                    }

                    if shots_elem:
                        player_stat['shots'] = int(shots_elem.get_text(strip=True))

                    stats.append(player_stat)
            except (ValueError, AttributeError):
                continue

        return stats

    def _parse_commentary(self, html: str) -> list[dict[str, str]]:
        """
        Parse live commentary from FlashScore HTML.

        Args:
            html: Raw HTML content from FlashScore match page

        Returns:
            List of commentary items with minute and text
        """
        from bs4 import Tag

        soup = BeautifulSoup(html, 'lxml')
        commentary: list[dict[str, str]] = []

        # Find commentary section
        commentary_section = soup.find('div', class_='commentary')
        if not commentary_section or not isinstance(commentary_section, Tag):
            return commentary

        # Find individual comment items
        comment_items = commentary_section.find_all('div', class_='comment-item')

        for comment_item in comment_items:
            if not isinstance(comment_item, Tag):
                continue

            try:
                minute_elem = comment_item.find('span', class_='minute')
                text_elem = comment_item.find('span', class_='text')

                if (minute_elem and text_elem and isinstance(minute_elem, Tag) and
                        isinstance(text_elem, Tag)):
                    commentary.append({
                        'minute': minute_elem.get_text(strip=True),
                        'text': text_elem.get_text(strip=True),
                    })
            except AttributeError:
                continue

        return commentary

    async def scrape_odds(self, match_id: str) -> dict[str, Any] | None:
        """
        Scrape odds for a specific match.

        Args:
            match_id: FlashScore match identifier

        Returns:
            Odds dictionary or None if not found

        Raises:
            Exception: If network request fails
        """
        url = self._get_match_url(match_id)
        html = await self.base_scraper.scrape(url)
        return self._parse_odds(html)

    async def scrape_lineups(self, match_id: str) -> dict[str, list[str]]:
        """
        Scrape team lineups for a specific match.

        Args:
            match_id: FlashScore match identifier

        Returns:
            Dictionary with 'home' and 'away' player lists

        Raises:
            Exception: If network request fails
        """
        url = self._get_match_url(match_id)
        html = await self.base_scraper.scrape(url)
        return self._parse_lineups(html)

    async def scrape_player_stats(self, match_id: str) -> list[dict[str, Any]]:
        """
        Scrape player statistics for a specific match.

        Args:
            match_id: FlashScore match identifier

        Returns:
            List of player stat dictionaries

        Raises:
            Exception: If network request fails
        """
        url = self._get_match_url(match_id)
        html = await self.base_scraper.scrape(url)
        return self._parse_player_stats(html)

    async def scrape_commentary(self, match_id: str) -> list[dict[str, str]]:
        """
        Scrape live commentary for a specific match.

        Args:
            match_id: FlashScore match identifier

        Returns:
            List of commentary items

        Raises:
            Exception: If network request fails
        """
        url = self._get_match_url(match_id)
        html = await self.base_scraper.scrape(url)
        return self._parse_commentary(html)
