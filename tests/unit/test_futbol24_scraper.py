"""
Unit tests for Futbol24 scraper.

Following TDD methodology: RED phase - these tests will fail until implementation.
"""

from unittest.mock import patch

import pytest

from sipap_batch_scraper.scrapers.futbol24 import Futbol24Scraper


class TestFutbol24Scraper:
    """Test suite for Futbol24 scraper."""

    @pytest.fixture
    def scraper(self):
        """Create Futbol24 scraper instance."""
        return Futbol24Scraper()

    @pytest.fixture
    def sample_html_matches(self):
        """Sample HTML with match listings."""
        return """
        <html>
            <body>
                <div class="match">
                    <div class="team-home">Manchester United</div>
                    <div class="team-away">Liverpool</div>
                    <div class="match-time">18:00</div>
                    <div class="competition">Premier League</div>
                </div>
                <div class="match">
                    <div class="team-home">Arsenal</div>
                    <div class="team-away">Chelsea</div>
                    <div class="match-time">20:30</div>
                    <div class="competition">Premier League</div>
                </div>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_html_live_match(self):
        """Sample HTML with live match."""
        return """
        <html>
            <body>
                <div class="match live">
                    <div class="team-home">Real Madrid</div>
                    <div class="team-away">Barcelona</div>
                    <div class="score">1 - 2</div>
                    <div class="match-time">72'</div>
                    <div class="competition">La Liga</div>
                </div>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_html_historical_match(self):
        """Sample HTML with historical match (finished)."""
        return """
        <html>
            <body>
                <div class="match finished">
                    <div class="team-home">Bayern Munich</div>
                    <div class="team-away">Borussia Dortmund</div>
                    <div class="score">3 - 1</div>
                    <div class="match-time">FT</div>
                    <div class="competition">Bundesliga</div>
                    <div class="match-date">2026-06-20</div>
                </div>
            </body>
        </html>
        """

    def test_scraper_initialization(self, scraper):
        """Test scraper initializes with default timeout."""
        assert scraper.base_url == "https://www.futbol24.com"
        assert scraper.timeout == 15000

    def test_scraper_custom_timeout(self):
        """Test scraper accepts custom timeout."""
        scraper = Futbol24Scraper(timeout=30000)
        assert scraper.timeout == 30000

    @pytest.mark.asyncio
    async def test_get_football_url(self, scraper):
        """Test football URL construction."""
        url = scraper._get_football_url()
        assert url == "https://www.futbol24.com/live/"

    @pytest.mark.asyncio
    async def test_get_football_url_with_date(self, scraper):
        """Test football URL with specific date."""
        date_str = "2026-06-27"
        url = scraper._get_football_url(date=date_str)
        # Futbol24 uses date in URL path or query parameter
        assert "futbol24.com" in url
        assert date_str in url or "date=" in url

    @pytest.mark.asyncio
    async def test_parse_matches_from_html(self, scraper, sample_html_matches):
        """Test parsing match data from HTML."""
        matches = scraper._parse_matches(sample_html_matches)

        assert len(matches) == 2

        # First match
        assert matches[0]['home_team'] == "Manchester United"
        assert matches[0]['away_team'] == "Liverpool"
        assert matches[0]['time'] == "18:00"
        assert matches[0]['league'] == "Premier League"

        # Second match
        assert matches[1]['home_team'] == "Arsenal"
        assert matches[1]['away_team'] == "Chelsea"
        assert matches[1]['time'] == "20:30"

    @pytest.mark.asyncio
    async def test_parse_live_match(self, scraper, sample_html_live_match):
        """Test parsing live match with score."""
        matches = scraper._parse_matches(sample_html_live_match)

        assert len(matches) == 1
        match = matches[0]

        assert match['home_team'] == "Real Madrid"
        assert match['away_team'] == "Barcelona"
        assert match['status'] == "live"
        assert match['score'] == "1 - 2"
        assert match['time'] == "72'"
        assert match['league'] == "La Liga"

    @pytest.mark.asyncio
    async def test_parse_historical_match(self, scraper, sample_html_historical_match):
        """Test parsing historical/finished match."""
        matches = scraper._parse_matches(sample_html_historical_match)

        assert len(matches) == 1
        match = matches[0]

        assert match['home_team'] == "Bayern Munich"
        assert match['away_team'] == "Borussia Dortmund"
        assert match['status'] == "finished"
        assert match['score'] == "3 - 1"
        assert match['time'] == "FT"
        assert match['league'] == "Bundesliga"
        # Historical matches may have date field
        if 'match_date' in match:
            assert match['match_date'] == "2026-06-20"

    @pytest.mark.asyncio
    async def test_parse_matches_empty_html(self, scraper):
        """Test parsing with no matches in HTML."""
        html = "<html><body></body></html>"
        matches = scraper._parse_matches(html)

        assert matches == []

    @pytest.mark.asyncio
    async def test_scrape_today_matches(self, scraper):
        """Test scraping today's matches."""
        mock_html = """
        <html>
            <body>
                <div class="match">
                    <div class="team-home">Arsenal</div>
                    <div class="team-away">Chelsea</div>
                    <div class="match-time">15:00</div>
                    <div class="competition">Premier League</div>
                </div>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            matches = await scraper.scrape_today_matches()

            assert len(matches) == 1
            assert matches[0]['home_team'] == "Arsenal"
            assert matches[0]['away_team'] == "Chelsea"

    @pytest.mark.asyncio
    async def test_scrape_matches_by_date(self, scraper):
        """Test scraping matches for specific date."""
        mock_html = """
        <html>
            <body>
                <div class="match">
                    <div class="team-home">Liverpool</div>
                    <div class="team-away">Man Utd</div>
                    <div class="match-time">20:00</div>
                    <div class="competition">Premier League</div>
                </div>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            matches = await scraper.scrape_matches(date="2026-06-28")

            assert len(matches) == 1
            assert matches[0]['home_team'] == "Liverpool"

    @pytest.mark.asyncio
    async def test_scrape_handles_missing_data_gracefully(self, scraper):
        """Test scraper handles incomplete match data."""
        html = """
        <html>
            <body>
                <div class="match">
                    <div class="team-home">Team A</div>
                    <!-- Missing away team -->
                    <div class="match-time">15:00</div>
                </div>
            </body>
        </html>
        """

        matches = scraper._parse_matches(html)

        # Should skip matches with missing required data
        # or include with None values
        assert isinstance(matches, list)

    @pytest.mark.asyncio
    async def test_extract_match_id(self, scraper):
        """Test extracting unique match ID from HTML."""
        html = """
        <div class="match" data-match-id="FT24_ABC123">
            <div class="team-home">Arsenal</div>
            <div class="team-away">Chelsea</div>
        </div>
        """

        matches = scraper._parse_matches(html)

        if matches:
            # Should extract ID if present
            assert 'external_id' in matches[0] or 'match_id' in matches[0]

    @pytest.mark.asyncio
    async def test_scraper_adds_source_field(self, scraper, sample_html_matches):
        """Test scraper adds source field to all matches."""
        matches = scraper._parse_matches(sample_html_matches)

        for match in matches:
            assert match['source'] == 'futbol24'

    @pytest.mark.asyncio
    async def test_scraper_adds_scraped_at_timestamp(self, scraper, sample_html_matches):
        """Test scraper adds timestamp to matches."""
        matches = scraper._parse_matches(sample_html_matches)

        for match in matches:
            assert 'scraped_at' in match
            # Should be ISO 8601 format
            assert isinstance(match['scraped_at'], str)

    @pytest.mark.asyncio
    async def test_scrape_with_network_error(self, scraper):
        """Test scraper handles network errors gracefully."""
        with patch.object(scraper.base_scraper, 'scrape', side_effect=Exception("Network error")):
            with pytest.raises(Exception):
                await scraper.scrape_today_matches()

    @pytest.mark.asyncio
    async def test_scrape_historical_matches(self, scraper):
        """Test scraping historical matches (Futbol24 unique feature)."""
        mock_html = """
        <html>
            <body>
                <div class="match finished">
                    <div class="team-home">PSG</div>
                    <div class="team-away">Monaco</div>
                    <div class="score">2 - 0</div>
                    <div class="match-time">FT</div>
                    <div class="competition">Ligue 1</div>
                    <div class="match-date">2026-05-15</div>
                </div>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            matches = await scraper.scrape_matches(date="2026-05-15")

            assert len(matches) == 1
            assert matches[0]['home_team'] == "PSG"
            assert matches[0]['status'] == "finished"
            assert matches[0]['score'] == "2 - 0"


class TestFutbol24ScraperPhase2:
    """Test suite for Futbol24 scraper Phase 2 features (detailed historical data extraction)."""

    @pytest.fixture
    def scraper(self):
        """Create Futbol24 scraper instance."""
        return Futbol24Scraper()

    @pytest.fixture
    def sample_html_h2h(self):
        """Sample HTML with head-to-head history."""
        return """
        <html>
            <body>
                <div class="h2h-container">
                    <div class="h2h-match">
                        <span class="h2h-date">2026-01-15</span>
                        <span class="h2h-home">Liverpool</span>
                        <span class="h2h-score">2 - 1</span>
                        <span class="h2h-away">Arsenal</span>
                    </div>
                    <div class="h2h-match">
                        <span class="h2h-date">2025-09-20</span>
                        <span class="h2h-home">Arsenal</span>
                        <span class="h2h-score">1 - 1</span>
                        <span class="h2h-away">Liverpool</span>
                    </div>
                </div>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_html_trends(self):
        """Sample HTML with team trends."""
        return """
        <html>
            <body>
                <div class="trends-container">
                    <div class="trend-stat">
                        <span class="stat-label">Last 5 matches</span>
                        <span class="stat-value">W W D L W</span>
                    </div>
                    <div class="trend-stat">
                        <span class="stat-label">Goals scored (avg)</span>
                        <span class="stat-value">2.1</span>
                    </div>
                    <div class="trend-stat">
                        <span class="stat-label">Goals conceded (avg)</span>
                        <span class="stat-value">1.3</span>
                    </div>
                </div>
            </body>
        </html>
        """

    @pytest.mark.asyncio
    async def test_parse_h2h(self, scraper, sample_html_h2h):
        """Test parsing head-to-head history from HTML."""
        h2h = scraper._parse_h2h(sample_html_h2h)

        assert len(h2h) == 2
        assert h2h[0]['date'] == "2026-01-15"
        assert h2h[0]['home_team'] == "Liverpool"
        assert h2h[0]['score'] == "2 - 1"
        assert h2h[0]['away_team'] == "Arsenal"

    @pytest.mark.asyncio
    async def test_parse_trends(self, scraper, sample_html_trends):
        """Test parsing team trends from HTML."""
        trends = scraper._parse_trends(sample_html_trends)

        assert 'last_5_matches' in trends
        assert trends['last_5_matches'] == "W W D L W"
        assert trends['goals_scored_avg'] == 2.1
        assert trends['goals_conceded_avg'] == 1.3

    @pytest.mark.asyncio
    async def test_scrape_h2h(self, scraper):
        """Test scraping head-to-head history."""
        mock_html = """
        <html>
            <body>
                <div class="h2h-container">
                    <div class="h2h-match">
                        <span class="h2h-date">2025-12-10</span>
                        <span class="h2h-home">Man City</span>
                        <span class="h2h-score">3 - 0</span>
                        <span class="h2h-away">Chelsea</span>
                    </div>
                </div>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            h2h = await scraper.scrape_h2h(team1="Man City", team2="Chelsea")

            assert len(h2h) >= 1
            assert h2h[0]['home_team'] == "Man City"

    @pytest.mark.asyncio
    async def test_scrape_trends(self, scraper):
        """Test scraping team trends."""
        mock_html = """
        <html>
            <body>
                <div class="trends-container">
                    <div class="trend-stat">
                        <span class="stat-label">Last 5 matches</span>
                        <span class="stat-value">W W W D W</span>
                    </div>
                </div>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            trends = await scraper.scrape_trends(team="Liverpool")

            assert 'last_5_matches' in trends

    @pytest.mark.asyncio
    async def test_get_h2h_url(self, scraper):
        """Test H2H URL construction."""
        url = scraper._get_h2h_url(team1="liverpool", team2="arsenal")
        assert "futbol24.com" in url
        assert "liverpool" in url.lower() or "arsenal" in url.lower()

    @pytest.mark.asyncio
    async def test_get_trends_url(self, scraper):
        """Test trends URL construction."""
        url = scraper._get_trends_url(team="liverpool")
        assert "futbol24.com" in url
        assert "liverpool" in url.lower()

    @pytest.mark.asyncio
    async def test_parse_h2h_empty_html(self, scraper):
        """Test parsing H2H with no matches."""
        html = "<html><body></body></html>"
        h2h = scraper._parse_h2h(html)
        assert h2h == []

    @pytest.mark.asyncio
    async def test_h2h_adds_source_field(self, scraper, sample_html_h2h):
        """Test H2H parsing adds source field."""
        h2h = scraper._parse_h2h(sample_html_h2h)
        if h2h:
            assert 'source' in h2h[0]
            assert h2h[0]['source'] == 'futbol24'

    @pytest.mark.asyncio
    async def test_trends_adds_scraped_at_timestamp(self, scraper, sample_html_trends):
        """Test trends parsing adds timestamp."""
        trends = scraper._parse_trends(sample_html_trends)
        if trends:
            assert 'scraped_at' in trends
            assert isinstance(trends['scraped_at'], str)
