"""
Utility functions for sipap-batch-scraper.

Provides helper utilities for common operations:
- Secrets Manager integration
- Configuration management
"""

from sipap_batch_scraper.util.secrets import get_secret

__all__ = ['get_secret']
