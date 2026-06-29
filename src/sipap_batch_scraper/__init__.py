"""
SIPAP Batch Scraper - Proactive sports data collection.

API-based batch data collection architecture for sports intelligence platform.
Decouples data collection from user requests to avoid rate limiting and improve performance.
"""

from sipap_batch_scraper.apis.football_data import FootballDataAPI
from sipap_batch_scraper.apis.odds_api import OddsAPI
from sipap_batch_scraper.apis.thesportsdb import TheSportsDBClient

__version__ = "0.2.0"

__all__ = ["FootballDataAPI", "OddsAPI", "TheSportsDBClient"]
