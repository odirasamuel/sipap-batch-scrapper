"""
Unit tests for FlashScore scraper.

Following TDD methodology: RED phase - these tests will fail until implementation.
"""

from unittest.mock import patch

import pytest

from sipap_batch_scraper.scrapers.flashscore import FlashScoreScraper


class TestFlashScoreScraper:
    """Test suite for FlashScore scraper."""

    @pytest.fixture
    def scraper(self):
        """Create FlashScore scraper instance."""
        return FlashScoreScraper()

    @pytest.fixture
    def sample_html_matches(self):
        """Sample HTML with match listings."""
        return """
        <html>
            <body>
                <div class="event__match">
                    <div class="event__participant--home">Arsenal</div>
                    <div class="event__participant--away">Chelsea</div>
                    <div class="event__time">15:00</div>
                    <div class="event__stage">Premier League</div>
                </div>
                <div class="event__match">
                    <div class="event__participant--home">Liverpool</div>
                    <div class="event__participant--away">Man City</div>
                    <div class="event__time">17:30</div>
                    <div class="event__stage">Premier League</div>
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
                <div class="event__match event__match--live">
                    <div class="event__participant--home">Barcelona</div>
                    <div class="event__participant--away">Real Madrid</div>
                    <div class="event__score">2 - 1</div>
                    <div class="event__time">67'</div>
                    <div class="event__stage">La Liga</div>
                </div>
            </body>
        </html>
        """

    def test_scraper_initialization(self, scraper):
        """Test scraper initializes with default timeout."""
        assert scraper.base_url == "https://www.flashscore.com"
        assert scraper.timeout == 15000

    def test_scraper_custom_timeout(self):
        """Test scraper accepts custom timeout."""
        scraper = FlashScoreScraper(timeout=30000)
        assert scraper.timeout == 30000

    @pytest.mark.asyncio
    async def test_get_football_url(self, scraper):
        """Test football URL construction."""
        url = scraper._get_football_url()
        assert url == "https://www.flashscore.com/football/"

    @pytest.mark.asyncio
    async def test_get_football_url_with_date(self, scraper):
        """Test football URL with specific date."""
        date_str = "2026-06-27"
        url = scraper._get_football_url(date=date_str)
        # FlashScore uses date query parameter
        assert "football" in url
        assert date_str in url or "?date=" in url

    @pytest.mark.asyncio
    async def test_parse_matches_from_html(self, scraper, sample_html_matches):
        """Test parsing match data from HTML."""
        matches = scraper._parse_matches(sample_html_matches)

        assert len(matches) == 2

        # First match
        assert matches[0]['home_team'] == "Arsenal"
        assert matches[0]['away_team'] == "Chelsea"
        assert matches[0]['time'] == "15:00"
        assert matches[0]['league'] == "Premier League"

        # Second match
        assert matches[1]['home_team'] == "Liverpool"
        assert matches[1]['away_team'] == "Man City"
        assert matches[1]['time'] == "17:30"

    @pytest.mark.asyncio
    async def test_parse_live_match(self, scraper, sample_html_live_match):
        """Test parsing live match with score."""
        matches = scraper._parse_matches(sample_html_live_match)

        assert len(matches) == 1
        match = matches[0]

        assert match['home_team'] == "Barcelona"
        assert match['away_team'] == "Real Madrid"
        assert match['status'] == "live"
        assert match['score'] == "2 - 1"
        assert match['time'] == "67'"
        assert match['league'] == "La Liga"

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
                <div class="event__match">
                    <div class="event__participant--home">Arsenal</div>
                    <div class="event__participant--away">Chelsea</div>
                    <div class="event__time">15:00</div>
                    <div class="event__stage">Premier League</div>
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
                <div class="event__match">
                    <div class="event__participant--home">Liverpool</div>
                    <div class="event__participant--away">Man Utd</div>
                    <div class="event__time">20:00</div>
                    <div class="event__stage">Premier League</div>
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
                <div class="event__match">
                    <div class="event__participant--home">Team A</div>
                    <!-- Missing away team -->
                    <div class="event__time">15:00</div>
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
        <div class="event__match" id="g_1_ABC123">
            <div class="event__participant--home">Arsenal</div>
            <div class="event__participant--away">Chelsea</div>
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
            assert match['source'] == 'flashscore'

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


class TestFlashScoreScraperPhase2:
    """Test suite for FlashScore scraper Phase 2 features (detailed data extraction)."""

    @pytest.fixture
    def scraper(self):
        """Create FlashScore scraper instance."""
        return FlashScoreScraper()

    @pytest.fixture
    def sample_html_odds(self):
        """Sample HTML with match odds."""
        return """
        <html>
            <body>
                <div class="odds-section">
                    <div class="odd-home">2.10</div>
                    <div class="odd-draw">3.20</div>
                    <div class="odd-away">3.50</div>
                </div>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_html_lineups(self):
        """Sample HTML with team lineups."""
        return """
        <html>
            <body>
                <div class="lineup-home">
                    <div class="player">Alisson</div>
                    <div class="player">Alexander-Arnold</div>
                    <div class="player">Van Dijk</div>
                </div>
                <div class="lineup-away">
                    <div class="player">Ederson</div>
                    <div class="player">Walker</div>
                    <div class="player">Dias</div>
                </div>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_html_player_stats(self):
        """Sample HTML with player statistics."""
        return """
        <html>
            <body>
                <div class="player-stats">
                    <div class="player-name">Salah</div>
                    <div class="goals">23</div>
                    <div class="assists">12</div>
                    <div class="shots">145</div>
                </div>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_html_commentary(self):
        """Sample HTML with live commentary."""
        return """
        <html>
            <body>
                <div class="commentary">
                    <div class="comment-item">
                        <span class="minute">67'</span>
                        <span class="text">GOAL! Salah scores for Liverpool</span>
                    </div>
                    <div class="comment-item">
                        <span class="minute">45'</span>
                        <span class="text">Half-time whistle</span>
                    </div>
                </div>
            </body>
        </html>
        """

    @pytest.mark.asyncio
    async def test_parse_odds(self, scraper, sample_html_odds):
        """Test parsing match odds from HTML."""
        odds = scraper._parse_odds(sample_html_odds)

        assert odds['home'] == 2.10
        assert odds['draw'] == 3.20
        assert odds['away'] == 3.50

    @pytest.mark.asyncio
    async def test_parse_lineups(self, scraper, sample_html_lineups):
        """Test parsing team lineups from HTML."""
        lineups = scraper._parse_lineups(sample_html_lineups)

        assert len(lineups['home']) == 3
        assert len(lineups['away']) == 3
        assert 'Alisson' in lineups['home']
        assert 'Ederson' in lineups['away']

    @pytest.mark.asyncio
    async def test_parse_player_stats(self, scraper, sample_html_player_stats):
        """Test parsing player statistics from HTML."""
        stats = scraper._parse_player_stats(sample_html_player_stats)

        assert len(stats) >= 1
        player = stats[0]
        assert player['name'] == 'Salah'
        assert player['goals'] == 23
        assert player['assists'] == 12

    @pytest.mark.asyncio
    async def test_parse_commentary(self, scraper, sample_html_commentary):
        """Test parsing live commentary from HTML."""
        commentary = scraper._parse_commentary(sample_html_commentary)

        assert len(commentary) == 2
        assert commentary[0]['minute'] == "67'"
        assert 'Salah scores' in commentary[0]['text']

    @pytest.mark.asyncio
    async def test_scrape_odds(self, scraper):
        """Test scraping odds for specific match."""
        mock_html = """
        <html>
            <body>
                <div class="odds-section">
                    <div class="odd-home">1.85</div>
                    <div class="odd-draw">3.40</div>
                    <div class="odd-away">4.20</div>
                </div>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            odds = await scraper.scrape_odds(match_id="ABC123")

            assert odds['home'] == 1.85
            assert odds['draw'] == 3.40
            assert odds['away'] == 4.20

    @pytest.mark.asyncio
    async def test_scrape_lineups(self, scraper):
        """Test scraping lineups for specific match."""
        mock_html = """
        <html>
            <body>
                <div class="lineup-home">
                    <div class="player">Player 1</div>
                    <div class="player">Player 2</div>
                </div>
                <div class="lineup-away">
                    <div class="player">Player 3</div>
                    <div class="player">Player 4</div>
                </div>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            lineups = await scraper.scrape_lineups(match_id="ABC123")

            assert len(lineups['home']) == 2
            assert len(lineups['away']) == 2

    @pytest.mark.asyncio
    async def test_scrape_player_stats(self, scraper):
        """Test scraping player stats for specific match."""
        mock_html = """
        <html>
            <body>
                <div class="player-stats">
                    <div class="player-name">Haaland</div>
                    <div class="goals">36</div>
                    <div class="assists">8</div>
                </div>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            stats = await scraper.scrape_player_stats(match_id="ABC123")

            assert len(stats) >= 1
            assert stats[0]['name'] == 'Haaland'

    @pytest.mark.asyncio
    async def test_scrape_commentary(self, scraper):
        """Test scraping live commentary for specific match."""
        mock_html = """
        <html>
            <body>
                <div class="commentary">
                    <div class="comment-item">
                        <span class="minute">90+3'</span>
                        <span class="text">Full-time whistle</span>
                    </div>
                </div>
            </body>
        </html>
        """

        with patch.object(scraper.base_scraper, 'scrape', return_value=mock_html):
            commentary = await scraper.scrape_commentary(match_id="ABC123")

            assert len(commentary) >= 1
            assert commentary[0]['minute'] == "90+3'"

    @pytest.mark.asyncio
    async def test_get_match_url(self, scraper):
        """Test match-specific URL construction."""
        match_id = "ABC123"
        url = scraper._get_match_url(match_id)
        assert "flashscore.com" in url
        assert match_id in url

    @pytest.mark.asyncio
    async def test_parse_odds_missing_data(self, scraper):
        """Test parsing odds with missing data."""
        html = "<html><body></body></html>"
        odds = scraper._parse_odds(html)
        # Should return None or empty dict
        assert odds is None or odds == {}

    @pytest.mark.asyncio
    async def test_odds_adds_source_field(self, scraper, sample_html_odds):
        """Test odds parsing adds source field."""
        odds = scraper._parse_odds(sample_html_odds)
        if odds:
            assert 'source' in odds
            assert odds['source'] == 'flashscore'

    @pytest.mark.asyncio
    async def test_odds_adds_scraped_at_timestamp(self, scraper, sample_html_odds):
        """Test odds parsing adds timestamp."""
        odds = scraper._parse_odds(sample_html_odds)
        if odds:
            assert 'scraped_at' in odds
            assert isinstance(odds['scraped_at'], str)
