"""
Base Scraper — Abstract Interface
===================================
Defines the contract all scrapers must follow.
Includes common utilities: HTTP fetching, retry logic,
rate limiting, and User-Agent rotation.
"""

import time
import random
import logging
import requests
from abc import ABC, abstractmethod
from typing import Optional
from config.settings import (
    USER_AGENTS,
    REQUEST_TIMEOUT,
    MIN_DELAY_BETWEEN_REQUESTS,
    MAX_DELAY_BETWEEN_REQUESTS,
    MAX_RETRIES,
)

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for all job scrapers.

    Subclasses must implement:
      - parse(html, source_config) -> list[dict]

    Each returned job dict should contain:
      - title: str
      - organization: str
      - url: str (absolute)
      - deadline: str (optional)
      - description: str (optional)
      - raw_html: str (optional)
      - source: str
      - source_type: str
    """

    def __init__(self):
        self.session = requests.Session()
        self._last_request_time = 0

    def _get_headers(self) -> dict:
        """Generate request headers with a random User-Agent."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }

    def _rate_limit(self):
        """Enforce delay between requests to be respectful."""
        elapsed = time.time() - self._last_request_time
        delay = random.uniform(MIN_DELAY_BETWEEN_REQUESTS, MAX_DELAY_BETWEEN_REQUESTS)
        if elapsed < delay:
            wait_time = delay - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.1f}s")
            time.sleep(wait_time)
        self._last_request_time = time.time()

    def fetch(self, url: str) -> Optional[str]:
        """
        Fetch a URL with retry logic, rate limiting, and error handling.
        Returns the HTML content as string, or None on failure.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._rate_limit()

                logger.info(f"Fetching [{attempt}/{MAX_RETRIES}]: {url}")
                import urllib3
                urllib3.disable_warnings()

                response = self.session.get(
                    url,
                    headers=self._get_headers(),
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=True,
                    verify=False,
                )
                response.raise_for_status()

                # Handle encoding
                response.encoding = response.apparent_encoding or "utf-8"
                logger.info(f"Successfully fetched: {url} ({len(response.text)} chars)")
                return response.text

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout fetching {url} (attempt {attempt}/{MAX_RETRIES})")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error for {url} (attempt {attempt}/{MAX_RETRIES})")
            except requests.exceptions.HTTPError as e:
                logger.warning(f"HTTP {e.response.status_code} for {url} (attempt {attempt}/{MAX_RETRIES})")
                if e.response.status_code in (403, 429):
                    # Blocked or rate limited — longer backoff
                    time.sleep(random.uniform(5, 15))
                elif e.response.status_code >= 500:
                    time.sleep(random.uniform(3, 8))
                else:
                    break  # Client error, don't retry
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error for {url}: {e}")
                break

            # Exponential backoff between retries
            if attempt < MAX_RETRIES:
                backoff = min(2 ** attempt + random.uniform(0, 1), 30)
                logger.debug(f"Retrying in {backoff:.1f}s...")
                time.sleep(backoff)

        logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts")
        return None

    @abstractmethod
    def parse(self, html: str, source_config: dict) -> list:
        """
        Parse HTML content and extract job listings.

        Args:
            html: Raw HTML string from fetch()
            source_config: Bank/source config dict from banks.py

        Returns:
            List of job dicts with keys:
              title, organization, url, deadline, description, raw_html, source, source_type
        """
        pass

    def scrape(self, source_config: dict) -> list:
        """
        Full scrape pipeline: fetch + parse.
        Returns list of extracted job dicts.
        """
        url = source_config.get("career_url", "")
        name = source_config.get("name", "Unknown")

        logger.info(f"═══ Scraping: {name} ═══")
        html = self.fetch(url)

        if html is None:
            logger.error(f"Could not fetch {name}")
            return []

        try:
            jobs = self.parse(html, source_config)
            logger.info(f"Found {len(jobs)} jobs from {name}")
            return jobs
        except Exception as e:
            logger.error(f"Error parsing {name}: {e}", exc_info=True)
            return []

    def make_absolute_url(self, base_url: str, relative_url: str) -> str:
        """Convert a relative URL to absolute."""
        if not relative_url:
            return base_url
        if relative_url.startswith(("http://", "https://")):
            return relative_url
        from urllib.parse import urljoin
        return urljoin(base_url, relative_url)
