"""
ESPN scraper for news intelligence.

Extracts realtime news, team updates, weather conditions, and expert commentary.
ESPN is the news intelligence specialist in the multi-source data strategy.
"""

from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup

from sipap_batch_scraper.scrapers.base import BaseScraper


class ESPNScraper:
    """
    Scraper for ESPN news and intelligence.

    ESPN provides:
    - Realtime news across all sports (unique value)
    - Team-specific news and updates
    - Weather conditions impacting matches
    - Expert commentary and analysis
    - Breaking news and injury reports

    Phase 1: News Extraction
    - Extracts news articles: title, content, publish time, URL, sport

    Future phases will add:
    - Detailed weather analysis
    - Expert predictions and commentary
    - Injury report tracking
    - Team morale indicators

    Usage:
        scraper = ESPNScraper(timeout=30000)
        soccer_news = await scraper.scrape_soccer_news()
        team_news = await scraper.scrape_team_news(team="liverpool")
    """

    def __init__(self, timeout: int = 15000) -> None:
        """
        Initialize ESPN scraper.

        Args:
            timeout: Page load timeout in milliseconds (default: 15000)
        """
        self.base_url = "https://www.espn.com"
        self.timeout = timeout
        self.base_scraper = BaseScraper(timeout=timeout)

    def _get_soccer_news_url(self) -> str:
        """
        Construct ESPN soccer news URL.

        Returns:
            Full URL for soccer news section
        """
        return f"{self.base_url}/soccer/"

    def _get_team_news_url(self, team_slug: str) -> str:
        """
        Construct ESPN team-specific news URL.

        Args:
            team_slug: Team identifier/slug (e.g., 'liverpool', 'arsenal')

        Returns:
            Full URL for team news
        """
        return f"{self.base_url}/soccer/team/_/name/{team_slug}"

    def _parse_news(self, html: str) -> list[dict[str, Any]]:
        """
        Parse news articles from ESPN HTML.

        Extracts structured news data using BeautifulSoup CSS selectors.

        Args:
            html: Raw HTML content from ESPN

        Returns:
            List of news article dictionaries with fields:
                - title: Article headline
                - content: Article text/summary
                - published_at: ISO 8601 publish timestamp
                - url: Link to full article
                - sport: Sport category (Soccer, Basketball, etc.)
                - team: Team name (if team-specific news)
                - weather: Weather conditions (if weather-related)
                - source: Always 'espn'
                - scraped_at: ISO 8601 timestamp

        Note:
            Skips articles with missing required data (title, content).
            Gracefully handles incomplete HTML elements.
        """
        soup = BeautifulSoup(html, 'lxml')
        articles: list[dict[str, Any]] = []
        scraped_at = datetime.now(UTC).isoformat()

        # Find all news article elements
        # ESPN uses class="news-article" for article containers
        article_elements = soup.find_all('article', class_='news-article')

        for article_elem in article_elements:
            try:
                # Extract title (headline)
                title_elem = article_elem.find('h2', class_='headline')
                if not title_elem:
                    # Try alternative selectors
                    title_elem = article_elem.find('h1')
                    if not title_elem:
                        continue  # Skip articles without title

                title = title_elem.get_text(strip=True)

                # Extract content
                content_elem = article_elem.find('div', class_='article-content')
                if not content_elem:
                    # Try alternative selectors
                    content_elem = article_elem.find('p')

                content = content_elem.get_text(strip=True) if content_elem else None

                # Skip articles missing required data
                if not content:
                    continue

                # Extract publish timestamp
                time_elem = article_elem.find('time', class_='timestamp')
                published_at = None
                if time_elem:
                    # Try datetime attribute first
                    published_at = time_elem.get('datetime')
                    if not published_at:
                        # Fall back to text content
                        published_at = time_elem.get_text(strip=True)

                # Extract article URL
                url = None
                link_elem = article_elem.find('a', class_='article-link')
                if link_elem:
                    href = link_elem.get('href', '')
                    if href:
                        # Make absolute URL if relative
                        url = href if href.startswith('http') else f"{self.base_url}{href}"

                # Extract sport tag
                sport_elem = article_elem.find('div', class_='sport-tag')
                sport = sport_elem.get_text(strip=True) if sport_elem else None

                # Extract team tag (if team-specific news)
                team_elem = article_elem.find('div', class_='team-tag')
                team = team_elem.get_text(strip=True) if team_elem else None

                # Extract weather tag (if weather-related)
                weather_elem = article_elem.find('div', class_='weather-tag')
                weather = weather_elem.get_text(strip=True) if weather_elem else None

                # Build article dictionary
                article = {
                    'title': title,
                    'content': content,
                    'source': 'espn',
                    'scraped_at': scraped_at,
                }

                # Add optional fields if present
                if published_at:
                    article['published_at'] = published_at
                if url:
                    article['url'] = url
                if sport:
                    article['sport'] = sport
                if team:
                    article['team'] = team
                if weather:
                    article['weather'] = weather

                articles.append(article)

            except Exception:
                # Skip malformed article elements
                continue

        return articles

    async def scrape_soccer_news(self) -> list[dict[str, Any]]:
        """
        Scrape soccer news from ESPN.

        Returns:
            List of news article dictionaries

        Raises:
            Exception: If network request fails
        """
        url = self._get_soccer_news_url()
        html = await self.base_scraper.scrape(url)
        return self._parse_news(html)

    async def scrape_team_news(self, team: str) -> list[dict[str, Any]]:
        """
        Scrape team-specific news from ESPN.

        Args:
            team: Team slug (e.g., 'liverpool', 'arsenal')

        Returns:
            List of news article dictionaries for specified team

        Raises:
            Exception: If network request fails

        Note:
            ESPN's unique value is realtime news - use this method
            for breaking team news, injury updates, transfer rumors.
        """
        url = self._get_team_news_url(team)
        html = await self.base_scraper.scrape(url)
        return self._parse_news(html)

    def _get_weather_url(self, match_id: str) -> str:
        """
        Construct ESPN weather URL for a specific match.

        Args:
            match_id: Match identifier

        Returns:
            Full URL for match weather details
        """
        return f"{self.base_url}/soccer/match/_/gameId/{match_id}/weather"

    def _get_injuries_url(self, team: str) -> str:
        """
        Construct ESPN injuries URL for a team.

        Args:
            team: Team slug

        Returns:
            Full URL for team injury reports
        """
        return f"{self.base_url}/soccer/team/_/name/{team}/injuries"

    def _get_expert_predictions_url(self, match_id: str) -> str:
        """
        Construct ESPN expert predictions URL for a match.

        Args:
            match_id: Match identifier

        Returns:
            Full URL for expert predictions/preview
        """
        return f"{self.base_url}/soccer/preview/_/gameId/{match_id}"

    def _parse_weather(self, html: str) -> dict[str, Any]:
        """
        Parse detailed weather conditions from ESPN HTML.

        Args:
            html: Raw HTML content from ESPN weather page

        Returns:
            Dictionary with weather details:
                - temperature: Temperature reading
                - wind_speed: Wind speed
                - precipitation: Precipitation conditions
                - visibility: Visibility distance
                - source: Always 'espn'
                - scraped_at: ISO 8601 timestamp
        """
        from bs4 import Tag

        soup = BeautifulSoup(html, 'lxml')
        weather: dict[str, Any] = {
            'source': 'espn',
            'scraped_at': datetime.now(UTC).isoformat()
        }

        # Find weather container
        weather_container = soup.find('div', class_='weather-container')
        if not weather_container or not isinstance(weather_container, Tag):
            return weather

        # Find individual weather details
        weather_details = weather_container.find_all('div', class_='weather-detail')

        for detail_elem in weather_details:
            if not isinstance(detail_elem, Tag):
                continue

            try:
                label_elem = detail_elem.find('span', class_='weather-label')
                value_elem = detail_elem.find('span', class_='weather-value')

                if not (isinstance(label_elem, Tag) and isinstance(value_elem, Tag)):
                    continue

                label = label_elem.get_text(strip=True).lower()
                value = value_elem.get_text(strip=True)

                # Map labels to dictionary keys
                if 'temperature' in label:
                    weather['temperature'] = value
                elif 'wind' in label:
                    weather['wind_speed'] = value
                elif 'precipitation' in label or 'rain' in label:
                    weather['precipitation'] = value
                elif 'visibility' in label:
                    weather['visibility'] = value
                else:
                    # Store other weather data with cleaned key
                    key = label.replace(' ', '_').replace('(', '').replace(')', '')
                    weather[key] = value

            except AttributeError:
                continue

        return weather

    def _parse_injuries(self, html: str) -> list[dict[str, Any]]:
        """
        Parse injury reports from ESPN HTML.

        Args:
            html: Raw HTML content from ESPN injuries page

        Returns:
            List of injury dictionaries with:
                - player: Player name
                - status: Injury status (Out, Doubtful, Questionable, Fit)
                - injury_type: Type of injury
                - return_date: Expected return date
                - source: Always 'espn'
        """
        from bs4 import Tag

        soup = BeautifulSoup(html, 'lxml')
        injuries: list[dict[str, Any]] = []

        # Find injury report container
        injury_report = soup.find('div', class_='injury-report')
        if not injury_report or not isinstance(injury_report, Tag):
            return injuries

        # Find individual injury items
        injury_items = injury_report.find_all('div', class_='injury-item')

        for item_elem in injury_items:
            if not isinstance(item_elem, Tag):
                continue

            try:
                player_elem = item_elem.find('span', class_='player-name')
                status_elem = item_elem.find('span', class_='injury-status')
                injury_type_elem = item_elem.find('span', class_='injury-type')
                return_date_elem = item_elem.find('span', class_='return-date')

                if not (isinstance(player_elem, Tag) and isinstance(status_elem, Tag)):
                    continue

                injury = {
                    'player': player_elem.get_text(strip=True),
                    'status': status_elem.get_text(strip=True),
                    'source': 'espn',
                }

                # Add optional fields
                if injury_type_elem and isinstance(injury_type_elem, Tag):
                    injury['injury_type'] = injury_type_elem.get_text(strip=True)

                if return_date_elem and isinstance(return_date_elem, Tag):
                    injury['return_date'] = return_date_elem.get_text(strip=True)

                injuries.append(injury)

            except AttributeError:
                continue

        return injuries

    def _parse_expert_predictions(self, html: str) -> list[dict[str, Any]]:
        """
        Parse expert predictions from ESPN HTML.

        Args:
            html: Raw HTML content from ESPN match preview page

        Returns:
            List of expert prediction dictionaries with:
                - expert: Expert name
                - prediction: Score prediction
                - reasoning: Reasoning/analysis
                - confidence: Confidence percentage
                - source: Always 'espn'
        """
        from bs4 import Tag

        soup = BeautifulSoup(html, 'lxml')
        predictions: list[dict[str, Any]] = []

        # Find expert predictions container
        predictions_container = soup.find('div', class_='expert-predictions')
        if not predictions_container or not isinstance(predictions_container, Tag):
            return predictions

        # Find individual prediction items
        prediction_items = predictions_container.find_all('div', class_='prediction-item')

        for item_elem in prediction_items:
            if not isinstance(item_elem, Tag):
                continue

            try:
                expert_elem = item_elem.find('span', class_='expert-name')
                prediction_elem = item_elem.find('span', class_='prediction')
                reasoning_elem = item_elem.find('span', class_='reasoning')
                confidence_elem = item_elem.find('span', class_='confidence')

                if not (isinstance(expert_elem, Tag) and isinstance(prediction_elem, Tag)):
                    continue

                prediction_dict = {
                    'expert': expert_elem.get_text(strip=True),
                    'prediction': prediction_elem.get_text(strip=True),
                    'source': 'espn',
                }

                # Add optional fields
                if reasoning_elem and isinstance(reasoning_elem, Tag):
                    prediction_dict['reasoning'] = reasoning_elem.get_text(strip=True)

                if confidence_elem and isinstance(confidence_elem, Tag):
                    prediction_dict['confidence'] = confidence_elem.get_text(strip=True)

                predictions.append(prediction_dict)

            except AttributeError:
                continue

        return predictions

    async def scrape_weather(self, match_id: str) -> dict[str, Any]:
        """
        Scrape weather conditions for a specific match.

        Args:
            match_id: ESPN match identifier

        Returns:
            Dictionary with weather details

        Raises:
            Exception: If network request fails

        Note:
            Weather is a key ESPN Phase 2 feature - provides game-time
            conditions that can impact match outcomes.
        """
        url = self._get_weather_url(match_id)
        html = await self.base_scraper.scrape(url)
        return self._parse_weather(html)

    async def scrape_injuries(self, team: str) -> list[dict[str, Any]]:
        """
        Scrape injury reports for a team.

        Args:
            team: Team slug

        Returns:
            List of injury report dictionaries

        Raises:
            Exception: If network request fails

        Note:
            Injury tracking is a key ESPN Phase 2 feature - provides
            real-time player availability information.
        """
        url = self._get_injuries_url(team)
        html = await self.base_scraper.scrape(url)
        return self._parse_injuries(html)

    async def scrape_expert_predictions(self, match_id: str) -> list[dict[str, Any]]:
        """
        Scrape expert predictions for a match.

        Args:
            match_id: ESPN match identifier

        Returns:
            List of expert prediction dictionaries

        Raises:
            Exception: If network request fails

        Note:
            Expert predictions are a key ESPN Phase 2 feature - provides
            analyst insights and reasoning for match outcomes.
        """
        url = self._get_expert_predictions_url(match_id)
        html = await self.base_scraper.scrape(url)
        return self._parse_expert_predictions(html)
