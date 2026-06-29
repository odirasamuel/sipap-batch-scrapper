"""
Web scrapers for sports data sources.

Provides specialized scrapers for FlashScore, Futbol24, and ESPN with anti-detection.
"""

from sipap_batch_scraper.scrapers.base import BaseScraper
from sipap_batch_scraper.scrapers.espn import ESPNScraper
from sipap_batch_scraper.scrapers.flashscore import FlashScoreScraper
from sipap_batch_scraper.scrapers.futbol24 import Futbol24Scraper

__all__ = ["BaseScraper", "ESPNScraper", "FlashScoreScraper", "Futbol24Scraper"]
