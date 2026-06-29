"""
SIPAP Batch Scraper - Proactive sports data collection.

Batch-first web scraping architecture for sports intelligence platform.
Decouples data collection from user requests to avoid rate limiting and improve performance.
"""

from sipap_batch_scraper.scrapers.base import BaseScraper

__version__ = "0.1.0"

__all__ = ["BaseScraper"]
