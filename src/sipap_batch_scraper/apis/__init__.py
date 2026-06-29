"""
Sports data API clients.

This package provides clients for various sports data APIs:
- Football-Data.org: Match fixtures, standings, teams (FREE - active)
- The Odds API: Betting odds from bookmakers (FREE - active)
- TheSportsDB: Team info, player stats, events, standings (FREE - active)
- API-Football: Comprehensive football data (PAID - placeholder)
"""

from sipap_batch_scraper.apis.football_data import FootballDataAPI
from sipap_batch_scraper.apis.odds_api import SPORT_KEYS, OddsAPI
from sipap_batch_scraper.apis.thesportsdb import LEAGUE_IDS, TheSportsDBClient

__all__ = [
    'FootballDataAPI',
    'OddsAPI',
    'TheSportsDBClient',
    'SPORT_KEYS',
    'LEAGUE_IDS',
]
