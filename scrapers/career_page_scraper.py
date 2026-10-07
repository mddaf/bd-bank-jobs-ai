"""
Career Page Scraper
=====================
Scrapes direct career/job pages from bank and financial institution websites.
Uses BeautifulSoup with multiple CSS selector fallbacks to handle
the variety of HTML structures across different bank websites.
"""

import re
import logging
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class CareerPageScraper(BaseScraper):
    """
    Scraper for direct bank career pages.

    Strategy:
    1. Try the configured CSS selectors first
    2. Fall back to intelligent auto-detection (links containing job-related keywords)
    3. Extract whatever metadata is available (title, link, deadline)
    """

    # Keywords that indicate a link is likely a job posting
    JOB_KEYWORDS = [
        "officer", "manager", "executive", "analyst", "teller",
        "assistant", "director", "head", "specialist", "trainee",
        "recruitment", "circular", "vacancy", "নিয়োগ", "বিজ্ঞপ্তি",
        "পদ", "কর্মকর্তা", "নিয়োগ বিজ্ঞপ্তি", "পরীক্ষা",
        "career", "job", "position", "hiring", "apply", "recruit",
    ]

    # Keywords that indicate a link is NOT a job posting
    EXCLUDE_KEYWORDS = [
        "privacy", "cookie", "terms", "contact", "about",
        "login", "register", "facebook", "twitter", "linkedin",
        "instagram", "youtube", "home", "branch", "atm",
        "product", "service", "loan", "deposit", "card",
        "board of director", "board of directors", "executive committee",
        "audit committee", "management committee", "shariah supervisory",
        "shariah council", "annual report", "financial statement",
        "investor relation", "tender", "procurement", "auction", "csr",
    ]

    def parse(self, html: str, source_config: dict) -> list:
        """
        Parse career page HTML to extract job listings.

        Uses a multi-strategy approach:
        1. Configured CSS selectors
        2. Table-based extraction
        3. Link-based auto-detection with keyword matching
        """
        soup = BeautifulSoup(html, "html5lib")
        base_url = source_config.get("career_url", "")
        org_name = source_config.get("name", "Unknown")
        scrape_cfg = source_config.get("scrape_config", {})

        jobs = []

        # Strategy 1: Try configured selectors
        jobs = self._parse_with_selectors(soup, scrape_cfg, base_url, org_name, source_config)

        # Strategy 2: If no results, try auto-detection
        if not jobs:
            logger.info(f"Configured selectors found nothing for {org_name}, trying auto-detection...")
            jobs = self._auto_detect_jobs(soup, base_url, org_name, source_config)

        # Deduplicate by URL within this scrape
        seen_urls = set()
        unique_jobs = []
        for job in jobs:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                unique_jobs.append(job)

        return unique_jobs

    def _parse_with_selectors(self, soup: BeautifulSoup, scrape_cfg: dict,
                               base_url: str, org_name: str, source_config: dict) -> list:
        """Try parsing using the configured CSS selectors."""
        jobs = []
        container_selector = scrape_cfg.get("job_container", "")

        if not container_selector:
            return jobs

        # Try each selector in the comma-separated list
        containers = []
        for selector in container_selector.split(","):
            selector = selector.strip()
            if selector:
                found = soup.select(selector)
                containers.extend(found)

        for container in containers:
            job = self._extract_job_from_element(
                container, scrape_cfg, base_url, org_name, source_config
            )
            if job:
                jobs.append(job)

        return jobs

    def _extract_job_from_element(self, element, scrape_cfg: dict,
                                   base_url: str, org_name: str, source_config: dict) -> dict:
        """Extract job information from a single HTML element."""
        # Extract title
        title = ""
        title_selectors = scrape_cfg.get("title_selector", "").split(",")
        for sel in title_selectors:
            sel = sel.strip()
            if sel:
                title_el = element.select_one(sel)
                if title_el:
                    title = title_el.get_text(strip=True)
                    if title:
                        break

        # If no title found from selectors, try the element's text
        if not title:
            title = element.get_text(strip=True)

        # Extract link
        url = ""
        link_el = element.select_one("a[href]")
        if link_el:
            url = self.make_absolute_url(base_url, link_el.get("href", ""))
        else:
            # Check if element itself is a link
            if element.name == "a" and element.get("href"):
                url = self.make_absolute_url(base_url, element["href"])

        # Extract deadline
        deadline = ""
        deadline_selectors = scrape_cfg.get("deadline_selector", "").split(",")
        for sel in deadline_selectors:
            sel = sel.strip()
            if sel:
                deadline_el = element.select_one(sel)
                if deadline_el:
                    deadline = deadline_el.get_text(strip=True)
                    if deadline:
                        break

        # Validate: must have at least a title and URL
        if not title or len(title) < 3:
            return None
        if not url or url == base_url:
            return None

        # Filter out non-job links
        title_lower = title.lower()
        if any(kw in title_lower for kw in self.EXCLUDE_KEYWORDS):
            if not any(kw in title_lower for kw in self.JOB_KEYWORDS):
                return None

        return {
            "title": self._clean_text(title),
            "organization": org_name,
            "url": url,
            "deadline": self._clean_text(deadline) if deadline else None,
            "description": self._clean_text(element.get_text(strip=True))[:500],
            "raw_html": str(element)[:2000],
            "source": source_config.get("short_name", "UNKNOWN"),
            "source_type": source_config.get("type", "unknown"),
        }

    def _auto_detect_jobs(self, soup: BeautifulSoup, base_url: str,
                           org_name: str, source_config: dict) -> list:
        """
        Automatic job detection using keyword matching on links.
        This is the fallback when configured selectors don't work.
        """
        jobs = []

        # Find all links on the page
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link.get("href", "")

            if not text or len(text) < 5:
                continue

            # Check if this link looks like a job posting
            text_lower = text.lower()
            href_lower = href.lower()
            combined = f"{text_lower} {href_lower}"

            is_job = any(kw in combined for kw in self.JOB_KEYWORDS)
            is_excluded = any(kw in combined for kw in self.EXCLUDE_KEYWORDS)

            if is_job and not is_excluded:
                url = self.make_absolute_url(base_url, href)

                # Try to find deadline near this link
                deadline = self._find_nearby_deadline(link)

                jobs.append({
                    "title": self._clean_text(text),
                    "organization": org_name,
                    "url": url,
                    "deadline": deadline,
                    "description": None,
                    "raw_html": str(link.parent)[:2000] if link.parent else str(link),
                    "source": source_config.get("short_name", "UNKNOWN"),
                    "source_type": source_config.get("type", "unknown"),
                })

        # Also check for PDF links (many banks post circulars as PDFs)
        for link in soup.find_all("a", href=re.compile(r"\.pdf$", re.IGNORECASE)):
            text = link.get_text(strip=True)
            href = link.get("href", "")

            if not text or len(text) < 5:
                continue

            text_lower = text.lower()
            is_job = any(kw in text_lower for kw in self.JOB_KEYWORDS)

            if is_job:
                url = self.make_absolute_url(base_url, href)
                jobs.append({
                    "title": self._clean_text(text),
                    "organization": org_name,
                    "url": url,
                    "deadline": self._find_nearby_deadline(link),
                    "description": f"[PDF Circular] {text}",
                    "raw_html": str(link.parent)[:2000] if link.parent else str(link),
                    "source": source_config.get("short_name", "UNKNOWN"),
                    "source_type": source_config.get("type", "unknown"),
                })

        return jobs

    def _find_nearby_deadline(self, element) -> str:
        """
        Try to find deadline information near a link element.
        Looks at siblings and parent elements for date-like text.
        """
        date_pattern = re.compile(
            r'\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}'  # DD-MM-YYYY or similar
            r'|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{2,4}'  # DD Month YYYY
            r'|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s+\d{2,4}',  # Month DD, YYYY
            re.IGNORECASE
        )

        # Check siblings
        for sibling in element.find_next_siblings(limit=3):
            text = sibling.get_text(strip=True)
            match = date_pattern.search(text)
            if match:
                return match.group()

        # Check parent
        if element.parent:
            text = element.parent.get_text(strip=True)
            match = date_pattern.search(text)
            if match:
                return match.group()

        return None

    def _clean_text(self, text: str) -> str:
        """Clean up extracted text — remove extra whitespace and control chars."""
        if not text:
            return ""
        # Remove control characters and excessive whitespace
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()
