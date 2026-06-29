"""
Unit tests for ESPN scraper.

Following TDD methodology: RED phase - these tests will fail until implementation.
ESPN is the news intelligence specialist - extracts realtime news, team updates, weather.
"""

from unittest.mock import patch

import pytest

from sipap_batch_scraper.scrapers.espn import ESPNScraper


class TestESPNScraper:
    """Test suite for ESPN scraper."""

    @pytest.fixture
    def scraper(self):
        """Create ESPN scraper instance."""
        return ESPNScraper()

    @pytest.fixture
    def sample_html_news_articles(self):
        """Sample HTML with news articles."""
        return """
        <html>
            <body>
                <article class="news-article">
                    <h2 class="headline">Liverpool signs new midfielder</h2>
                    <div class="article-content">
                        Liverpool FC announced today the signing of a new midfielder
                        from Real Madrid for a record fee.
                    </div>
                    <time class="timestamp">2026-06-27T10:30:00Z</time>
                    <a class="article-link" href="/soccer/liverpool-signing">Read more</a>
                    <div class="sport-tag">Soccer</div>
                </article>
                <article class="news-article">
                    <h2 class="headline">Arsenal injury update ahead of derby</h2>
                    <div class="article-content">
                        Arsenal manager confirms three key players out for weekend derby.
                    </div>
                    <time class="timestamp">2026-06-27T09:15:00Z</time>
                    <a class="article-link" href="/soccer/arsenal-injuries">Read more</a>
                    <div class="sport-tag">Soccer</div>
                </article>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_html_weather_news(self):
        """Sample HTML with weather-related news."""
        return """
        <html>
            <body>
                <article class="news-article">
                    <h2 class="headline">Heavy rain expected for Man United vs Chelsea</h2>
                    <div class="article-content">
                        Weather conditions could impact Sunday's Premier League clash
                        with heavy rain and strong winds forecast.
                    </div>
                    <time class="timestamp">2026-06-27T08:00:00Z</time>
                    <div class="sport-tag">Soccer</div>
                    <div class="weather-tag">Rain, Wind</div>
                </article>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_html_team_news(self):
        """Sample HTML with team-specific news."""
        return """
        <html>
            <body>
                <article class="news-article team-news">
                    <h2 class="headline">Barcelona announces new coach</h2>
                    <div class="article-content">
                        Barcelona has appointed a new head coach following recent results.
                    </div>
                    <time class="timestamp">2026-06-27T11:00:00Z</time>
                    <div class="team-tag">Barcelona</div>
                    <div class="sport-tag">Soccer</div>
                </article>
            </body>
        </html>
        """

    def test_scraper_initialization(self, scraper):
        """Test scraper initializes with default timeout."""
        assert scraper.base_url == "https://www.espn.com"
        assert scraper.timeout == 15000

    def test_scraper_custom_timeout(self):
        """Test scraper accepts custom timeout."""
        scraper = ESPNScraper(timeout=30000)
        assert scraper.timeout == 30000

    @pytest.mark.asyncio
    async def test_get_soccer_news_url(self, scraper):
        """Test soccer news URL construction."""
        url = scraper._get_soccer_news_url()
        assert url == "https://www.espn.com/soccer/"

    @pytest.mark.asyncio
    async def test_get_team_news_url(self, scraper):
        """Test team-specific news URL construction."""
        team_slug = "liverpool"
        url = scraper._get_team_news_url(team_slug)
        assert "espn.com" in url
        assert "liverpool" in url.lower()

    @pytest.mark.asyncio
    async def test_parse_news_articles_from_html(self, scraper, sample_html_news_articles):
        """Test parsing news articles from HTML."""
        articles = scraper._parse_news(sample_html_news_articles)

        assert len(articles) == 2

        # First article
        assert articles[0]['title'] == "Liverpool signs new midfielder"
        assert "Liverpool FC announced" in articles[0]['content']
        assert articles[0]['published_at'] == "2026-06-27T10:30:00Z"
        assert articles[0]['sport'] == "Soccer"

        # Second article
        assert articles[1]['title'] == "Arsenal injury update ahead of derby"
        assert "three key players" in articles[1]['content']

    @pytest.mark.asyncio
    async def test_parse_weather_news(self, scraper, sample_html_weather_news):
        """Test parsing weather-related news."""
        articles = scraper._parse_news(sample_html_weather_news)

        assert len(articles) == 1
        article = articles[0]

        assert "Heavy rain" in article['title']
        assert "weather conditions" in article['content'].lower()
        # Weather tags if present
        if 'weather' in article:
            assert 'rain' in article['weather'].lower() or 'wind' in article['weather'].lower()

    @pytest.mark.asyncio
    async def test_parse_team_news(self, scraper, sample_html_team_news):
        """Test parsing team-specific news."""
        articles = scraper._parse_news(sample_html_team_news)

        assert len(articles) == 1
        article = articles[0]

        assert "Barcelona" in article['title']
        assert article['sport'] == "Soccer"
        # Team tag if present
        if 'team' in article:
            assert article['team'] == "Barcelona"

    @pytest.mark.asyncio
    async def test_parse_news_empty_html(self, scraper):
        """Test parsing with no news in HTML."""
        html = "<html><body></body></html>"
        articles = scraper._parse_news(html)

        assert articles == []

    @pytest.mark.asyncio
    async def test_scrape_soccer_news(self, scraper):
        """Test scraping soccer news."""
        mock_html = """
        <html>
            <body>
                <article class="news-article">
                    <h2 class="headline">Liverpool wins title</h2>
                    <div class="article-content">Liverpool clinches the league.</div>
                    <time class="timestamp">2026-06-27T12:00:00Z</time>
                    <div class="sport-tag">Soccer</div>
                </article>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            articles = await scraper.scrape_soccer_news()

            assert len(articles) == 1
            assert articles[0]['title'] == "Liverpool wins title"
            assert articles[0]['sport'] == "Soccer"

    @pytest.mark.asyncio
    async def test_scrape_team_news(self, scraper):
        """Test scraping team-specific news."""
        mock_html = """
        <html>
            <body>
                <article class="news-article">
                    <h2 class="headline">Arsenal transfers</h2>
                    <div class="article-content">Arsenal makes new signing.</div>
                    <time class="timestamp">2026-06-27T13:00:00Z</time>
                    <div class="sport-tag">Soccer</div>
                </article>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            articles = await scraper.scrape_team_news(team="arsenal")

            assert len(articles) == 1
            assert articles[0]['title'] == "Arsenal transfers"

    @pytest.mark.asyncio
    async def test_scrape_handles_missing_data_gracefully(self, scraper):
        """Test scraper handles incomplete news data."""
        html = """
        <html>
            <body>
                <article class="news-article">
                    <h2 class="headline">Title only</h2>
                    <!-- Missing content -->
                </article>
            </body>
        </html>
        """

        articles = scraper._parse_news(html)

        # Should skip articles with missing required data
        # or include with None values
        assert isinstance(articles, list)

    @pytest.mark.asyncio
    async def test_extract_article_url(self, scraper):
        """Test extracting article URL from HTML."""
        html = """
        <article class="news-article">
            <h2 class="headline">Test Article</h2>
            <div class="article-content">Content here.</div>
            <a class="article-link" href="/soccer/test-article">Read more</a>
        </article>
        """

        articles = scraper._parse_news(html)

        if articles:
            # Should extract URL if present
            assert 'url' in articles[0]
            assert '/soccer/test-article' in articles[0]['url']

    @pytest.mark.asyncio
    async def test_scraper_adds_source_field(self, scraper, sample_html_news_articles):
        """Test scraper adds source field to all articles."""
        articles = scraper._parse_news(sample_html_news_articles)

        for article in articles:
            assert article['source'] == 'espn'

    @pytest.mark.asyncio
    async def test_scraper_adds_scraped_at_timestamp(self, scraper, sample_html_news_articles):
        """Test scraper adds timestamp to articles."""
        articles = scraper._parse_news(sample_html_news_articles)

        for article in articles:
            assert 'scraped_at' in article
            # Should be ISO 8601 format
            assert isinstance(article['scraped_at'], str)

    @pytest.mark.asyncio
    async def test_scrape_with_network_error(self, scraper):
        """Test scraper handles network errors gracefully."""
        with patch.object(scraper.base_scraper, 'scrape', side_effect=Exception("Network error")):
            with pytest.raises(Exception):
                await scraper.scrape_soccer_news()

    @pytest.mark.asyncio
    async def test_filter_news_by_sport(self, scraper):
        """Test filtering news articles by sport."""
        html = """
        <html>
            <body>
                <article class="news-article">
                    <h2 class="headline">Soccer news</h2>
                    <div class="article-content">Soccer content.</div>
                    <div class="sport-tag">Soccer</div>
                </article>
                <article class="news-article">
                    <h2 class="headline">Basketball news</h2>
                    <div class="article-content">Basketball content.</div>
                    <div class="sport-tag">Basketball</div>
                </article>
            </body>
        </html>
        """

        articles = scraper._parse_news(html)

        # Should extract all articles with sport tags
        assert len(articles) == 2
        assert articles[0]['sport'] == "Soccer"
        assert articles[1]['sport'] == "Basketball"

    @pytest.mark.asyncio
    async def test_extract_publish_timestamp(self, scraper, sample_html_news_articles):
        """Test extracting article publish timestamp."""
        articles = scraper._parse_news(sample_html_news_articles)

        for article in articles:
            assert 'published_at' in article
            # Should be ISO 8601 format from <time> element
            assert isinstance(article['published_at'], str)


class TestESPNScraperPhase2:
    """Test suite for ESPN scraper Phase 2 features (weather, injuries, expert predictions)."""

    @pytest.fixture
    def scraper(self):
        """Create ESPN scraper instance."""
        return ESPNScraper()

    @pytest.fixture
    def sample_html_weather(self):
        """Sample HTML with detailed weather conditions."""
        return """
        <html>
            <body>
                <div class="weather-container">
                    <div class="weather-detail">
                        <span class="weather-label">Temperature</span>
                        <span class="weather-value">18°C</span>
                    </div>
                    <div class="weather-detail">
                        <span class="weather-label">Wind Speed</span>
                        <span class="weather-value">25 km/h</span>
                    </div>
                    <div class="weather-detail">
                        <span class="weather-label">Precipitation</span>
                        <span class="weather-value">Heavy Rain</span>
                    </div>
                    <div class="weather-detail">
                        <span class="weather-label">Visibility</span>
                        <span class="weather-value">5 km</span>
                    </div>
                </div>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_html_injuries(self):
        """Sample HTML with injury reports."""
        return """
        <html>
            <body>
                <div class="injury-report">
                    <div class="injury-item">
                        <span class="player-name">Mohamed Salah</span>
                        <span class="injury-status">Out</span>
                        <span class="injury-type">Hamstring</span>
                        <span class="return-date">2026-07-05</span>
                    </div>
                    <div class="injury-item">
                        <span class="player-name">Virgil van Dijk</span>
                        <span class="injury-status">Doubtful</span>
                        <span class="injury-type">Ankle</span>
                        <span class="return-date">Game-time decision</span>
                    </div>
                </div>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_html_expert_predictions(self):
        """Sample HTML with expert predictions."""
        return """
        <html>
            <body>
                <div class="expert-predictions">
                    <div class="prediction-item">
                        <span class="expert-name">Michael Owen</span>
                        <span class="prediction">Liverpool 2-1 Arsenal</span>
                        <span class="reasoning">
                            Liverpool's home form has been exceptional this season.
                            Arsenal struggling with key injuries in defense.
                        </span>
                        <span class="confidence">75%</span>
                    </div>
                    <div class="prediction-item">
                        <span class="expert-name">Jamie Carragher</span>
                        <span class="prediction">Liverpool 3-0 Arsenal</span>
                        <span class="reasoning">
                            Arsenal missing too many players. Liverpool too strong at Anfield.
                        </span>
                        <span class="confidence">80%</span>
                    </div>
                </div>
            </body>
        </html>
        """

    @pytest.mark.asyncio
    async def test_parse_weather(self, scraper, sample_html_weather):
        """Test parsing detailed weather conditions from HTML."""
        weather = scraper._parse_weather(sample_html_weather)

        assert 'temperature' in weather
        assert weather['temperature'] == "18°C"
        assert 'wind_speed' in weather
        assert weather['wind_speed'] == "25 km/h"
        assert 'precipitation' in weather
        assert weather['precipitation'] == "Heavy Rain"
        assert 'visibility' in weather
        assert weather['visibility'] == "5 km"

    @pytest.mark.asyncio
    async def test_parse_injuries(self, scraper, sample_html_injuries):
        """Test parsing injury reports from HTML."""
        injuries = scraper._parse_injuries(sample_html_injuries)

        assert len(injuries) == 2
        assert injuries[0]['player'] == "Mohamed Salah"
        assert injuries[0]['status'] == "Out"
        assert injuries[0]['injury_type'] == "Hamstring"
        assert injuries[0]['return_date'] == "2026-07-05"

        assert injuries[1]['player'] == "Virgil van Dijk"
        assert injuries[1]['status'] == "Doubtful"

    @pytest.mark.asyncio
    async def test_parse_expert_predictions(self, scraper, sample_html_expert_predictions):
        """Test parsing expert predictions from HTML."""
        predictions = scraper._parse_expert_predictions(sample_html_expert_predictions)

        assert len(predictions) == 2
        assert predictions[0]['expert'] == "Michael Owen"
        assert predictions[0]['prediction'] == "Liverpool 2-1 Arsenal"
        assert "home form" in predictions[0]['reasoning'].lower()
        assert predictions[0]['confidence'] == "75%"

        assert predictions[1]['expert'] == "Jamie Carragher"
        assert predictions[1]['confidence'] == "80%"

    @pytest.mark.asyncio
    async def test_scrape_weather(self, scraper):
        """Test scraping weather for a specific match."""
        mock_html = """
        <html>
            <body>
                <div class="weather-container">
                    <div class="weather-detail">
                        <span class="weather-label">Temperature</span>
                        <span class="weather-value">22°C</span>
                    </div>
                    <div class="weather-detail">
                        <span class="weather-label">Wind Speed</span>
                        <span class="weather-value">15 km/h</span>
                    </div>
                </div>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            weather = await scraper.scrape_weather(match_id="12345")

            assert 'temperature' in weather
            assert weather['temperature'] == "22°C"

    @pytest.mark.asyncio
    async def test_scrape_injuries(self, scraper):
        """Test scraping injury reports for a team."""
        mock_html = """
        <html>
            <body>
                <div class="injury-report">
                    <div class="injury-item">
                        <span class="player-name">Erling Haaland</span>
                        <span class="injury-status">Fit</span>
                        <span class="injury-type">-</span>
                    </div>
                </div>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            injuries = await scraper.scrape_injuries(team="manchester-city")

            assert len(injuries) >= 1
            assert injuries[0]['player'] == "Erling Haaland"
            assert injuries[0]['status'] == "Fit"

    @pytest.mark.asyncio
    async def test_scrape_expert_predictions(self, scraper):
        """Test scraping expert predictions for a match."""
        mock_html = """
        <html>
            <body>
                <div class="expert-predictions">
                    <div class="prediction-item">
                        <span class="expert-name">Gary Neville</span>
                        <span class="prediction">Man City 4-1 Tottenham</span>
                        <span class="reasoning">City too strong at home.</span>
                        <span class="confidence">90%</span>
                    </div>
                </div>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            predictions = await scraper.scrape_expert_predictions(match_id="67890")

            assert len(predictions) >= 1
            assert predictions[0]['expert'] == "Gary Neville"
            assert predictions[0]['confidence'] == "90%"

    @pytest.mark.asyncio
    async def test_get_weather_url(self, scraper):
        """Test weather URL construction."""
        match_id = "ABC123"
        url = scraper._get_weather_url(match_id)
        assert "espn.com" in url
        assert match_id in url or "weather" in url.lower()

    @pytest.mark.asyncio
    async def test_get_injuries_url(self, scraper):
        """Test injuries URL construction."""
        team = "liverpool"
        url = scraper._get_injuries_url(team)
        assert "espn.com" in url
        assert "liverpool" in url.lower() or "injuries" in url.lower()

    @pytest.mark.asyncio
    async def test_get_expert_predictions_url(self, scraper):
        """Test expert predictions URL construction."""
        match_id = "XYZ789"
        url = scraper._get_expert_predictions_url(match_id)
        assert "espn.com" in url
        assert match_id in url or "predictions" in url.lower() or "preview" in url.lower()

    @pytest.mark.asyncio
    async def test_parse_weather_empty_html(self, scraper):
        """Test parsing weather with no data."""
        html = "<html><body></body></html>"
        weather = scraper._parse_weather(html)
        assert isinstance(weather, dict)
        # Should return empty dict or dict with scraped_at only

    @pytest.mark.asyncio
    async def test_parse_injuries_empty_html(self, scraper):
        """Test parsing injuries with no reports."""
        html = "<html><body></body></html>"
        injuries = scraper._parse_injuries(html)
        assert injuries == []

    @pytest.mark.asyncio
    async def test_parse_expert_predictions_empty_html(self, scraper):
        """Test parsing expert predictions with no data."""
        html = "<html><body></body></html>"
        predictions = scraper._parse_expert_predictions(html)
        assert predictions == []

    @pytest.mark.asyncio
    async def test_weather_adds_source_field(self, scraper, sample_html_weather):
        """Test weather parsing adds source field."""
        weather = scraper._parse_weather(sample_html_weather)
        if weather:
            assert 'source' in weather
            assert weather['source'] == 'espn'

    @pytest.mark.asyncio
    async def test_weather_adds_scraped_at_timestamp(self, scraper, sample_html_weather):
        """Test weather parsing adds timestamp."""
        weather = scraper._parse_weather(sample_html_weather)
        if weather:
            assert 'scraped_at' in weather
            assert isinstance(weather['scraped_at'], str)

    @pytest.mark.asyncio
    async def test_injuries_add_source_field(self, scraper, sample_html_injuries):
        """Test injury parsing adds source field."""
        injuries = scraper._parse_injuries(sample_html_injuries)
        if injuries:
            assert 'source' in injuries[0]
            assert injuries[0]['source'] == 'espn'

    @pytest.mark.asyncio
    async def test_expert_predictions_add_source_field(
        self, scraper, sample_html_expert_predictions
    ):
        """Test expert prediction parsing adds source field."""
        predictions = scraper._parse_expert_predictions(
            sample_html_expert_predictions
        )
        if predictions:
            assert 'source' in predictions[0]
            assert predictions[0]['source'] == 'espn'
