"""
bdjobs.com Scraper
====================
Specialized scraper for bdjobs.com — the largest job portal in Bangladesh.
Focuses on the Bank/Non-Bank Financial Institution category.
"""

import re
import logging
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class BdjobsScraper(BaseScraper):
    """
    Scraper for bdjobs.com banking category.

    bdjobs.com typically lists jobs in a structured format with:
    - Job title link
    - Company name
    - Deadline
    - Experience and education requirements
    """

    # Multiple category URLs to cover banking jobs
    CATEGORY_URLS = [
        "https://jobs.bdjobs.com/jobsearch.asp?fcatId=8",   # Bank/Non-Bank Fin. Institution
        "https://jobs.bdjobs.com/jobsearch.asp?fcatId=14",  # Financial Institution/Market
    ]

    def scrape_all_categories(self) -> list:
        """Scrape all banking-related categories from bdjobs.com."""
        all_jobs = []
        seen_urls = set()

        for url in self.CATEGORY_URLS:
            source_config = {
                "name": "bdjobs.com",
                "short_name": "BDJOBS",
                "type": "job_portal",
                "career_url": url,
                "scrape_config": {},
            }

            html = self.fetch(url)
            if html:
                jobs = self.parse(html, source_config)
                for job in jobs:
                    if job["url"] not in seen_urls:
                        seen_urls.add(job["url"])
                        all_jobs.append(job)

        logger.info(f"Total unique jobs from bdjobs.com: {len(all_jobs)}")
        return all_jobs

    def parse(self, html: str, source_config: dict) -> list:
        """Parse bdjobs.com search results page."""
        soup = BeautifulSoup(html, "html5lib")
        base_url = source_config.get("career_url", "https://jobs.bdjobs.com")
        jobs = []

        # Strategy 1: Look for structured job listing blocks
        # bdjobs.com uses various container classes over time
        job_containers = soup.select(
            ".job-list-container .job-item, "
            ".norm, "
            ".topjob-block, "
            ".featured-block, "
            "table.job-list-table tbody tr, "
            ".job_list_row, "
            "div[class*='job']"
        )

        for container in job_containers:
            job = self._extract_bdjobs_listing(container, base_url)
            if job:
                jobs.append(job)

        # Strategy 2: If structured parsing fails, look for all job links
        if not jobs:
            logger.info("Structured bdjobs parsing failed, trying link extraction...")
            jobs = self._extract_from_links(soup, base_url)

        return jobs

    def _extract_bdjobs_listing(self, container, base_url: str) -> dict:
        """Extract job details from a bdjobs.com listing container."""
        # Find the job title link
        title_link = None
        for selector in ["a.title", ".job-title a", "a[href*='jobdetails']", "a[href*='JobId']", "a"]:
            title_link = container.select_one(selector)
            if title_link and title_link.get("href"):
                break

        if not title_link:
            return None

        title = title_link.get_text(strip=True)
        href = title_link.get("href", "")

        if not title or len(title) < 3:
            return None

        url = self.make_absolute_url(base_url, href)

        # Extract company name
        company = "Unknown"
        for selector in [".comp-name", ".company-name", ".comp_name", "span.company"]:
            comp_el = container.select_one(selector)
            if comp_el:
                company = comp_el.get_text(strip=True)
                break

        # If company not found, check for text near the title
        if company == "Unknown":
            all_text = container.get_text(" ", strip=True)
            # Sometimes company name is in parentheses or after a separator
            parts = re.split(r'[|\-–]', all_text)
            if len(parts) > 1:
                potential_company = parts[1].strip()
                if len(potential_company) > 3 and len(potential_company) < 100:
                    company = potential_company

        # Extract deadline
        deadline = None
        for selector in [".job-deadline", ".dead-line", ".deadline", "span[class*='dead']"]:
            deadline_el = container.select_one(selector)
            if deadline_el:
                deadline = deadline_el.get_text(strip=True)
                break

        # Filter: only keep banking/finance related jobs
        if not self._is_banking_related(title, company):
            return None

        return {
            "title": self._clean_text(title),
            "organization": self._clean_text(company),
            "url": url,
            "deadline": self._clean_text(deadline) if deadline else None,
            "description": self._clean_text(container.get_text(" ", strip=True))[:500],
            "raw_html": str(container)[:2000],
            "source": "BDJOBS",
            "source_type": "job_portal",
        }

    def _extract_from_links(self, soup: BeautifulSoup, base_url: str) -> list:
        """Fallback: extract jobs from links containing job-related patterns."""
        jobs = []

        for link in soup.find_all("a", href=re.compile(r"jobdetails|JobId|job_id", re.IGNORECASE)):
            title = link.get_text(strip=True)
            href = link.get("href", "")

            if not title or len(title) < 5:
                continue

            url = self.make_absolute_url(base_url, href)

            jobs.append({
                "title": self._clean_text(title),
                "organization": "Via bdjobs.com",
                "url": url,
                "deadline": None,
                "description": None,
                "raw_html": str(link.parent)[:2000] if link.parent else str(link),
                "source": "BDJOBS",
                "source_type": "job_portal",
            })

        return jobs

    def _is_banking_related(self, title: str, company: str) -> bool:
        """Check if a job listing is related to banking/finance."""
        banking_keywords = [
            "bank", "finance", "financial", "credit", "loan",
            "investment", "treasury", "banking", "microfinance",
            "insurance", "capital", "securities", "asset",
            "ব্যাংক", "অর্থ", "বিনিয়োগ", "ঋণ",
        ]

        combined = f"{title} {company}".lower()
        return any(kw in combined for kw in banking_keywords)

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()
