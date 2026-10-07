"""
bdjobs.com Scraper
====================
Specialized scraper for bdjobs.com — the largest job portal in Bangladesh.
Uses bdjobs.com's high-speed JSON Search API with multi-keyword targeting,
falling back to HTML card parsing if the API is temporarily unreachable.
"""

import re
import logging
from typing import List, Dict, Optional
import urllib3
import requests
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper

urllib3.disable_warnings()
logger = logging.getLogger(__name__)


class BdjobsScraper(BaseScraper):
    """
    High-performance scraper for bdjobs.com banking & financial postings.
    Queries official search endpoints for banking, finance, NBFI, and microfinance roles.
    """

    API_URL = "https://api.bdjobs.com/Jobs/api/JobSearch/GetJobSearch"

    # Targeted search keywords to cover all bank & financial institution jobs
    SEARCH_KEYWORDS = ["bank", "banking", "financial", "NBFI", "microfinance"]

    # Keywords to ensure job relevance
    BANKING_KEYWORDS = [
        "bank", "banking", "nbfi", "financial", "finance", "credit", "loan",
        "investment", "treasury", "microfinance", "insurance", "capital",
        "securities", "asset", "branch", "cash", "remittance", "compliance",
        "auditor", "audit", "aml", "cft", "ব্যাংক", "অর্থ", "বিনিয়োগ", "ঋণ"
    ]

    def scrape_all_categories(self) -> List[Dict]:
        """Scrape all banking-related jobs from bdjobs.com."""
        all_jobs = []
        seen_job_ids = set()

        # Step 1: Use official Bdjobs Search API
        for keyword in self.SEARCH_KEYWORDS:
            try:
                params = {
                    "keyword": keyword,
                    "rpp": 50,
                    "pg": 1,
                    "isPro": 0,
                    "ToggleJobs": "true",
                    "isFresher": "false",
                }
                headers = self._get_headers()
                response = self.session.get(
                    self.API_URL,
                    params=params,
                    headers=headers,
                    timeout=10,
                    verify=False,
                )

                if response.status_code == 200:
                    data = response.json()
                    jobs_data = data.get("data", []) + (data.get("premiumData") or [])
                    for item in jobs_data:
                        jid = str(item.get("Jobid") or "").strip()
                        if not jid or jid in seen_job_ids:
                            continue

                        title = item.get("jobTitle") or ""
                        company = item.get("companyName") or "Bank/Financial Institution"
                        
                        # Filter to only keep relevant banking/financial jobs
                        if not self._is_banking_related(title, company):
                            continue

                        seen_job_ids.add(jid)
                        deadline = item.get("deadline") or None
                        url = f"https://jobs.bdjobs.com/jobdetails/?id={jid}"
                        desc = item.get("jobDescription") or item.get("eduRec") or ""
                        location = item.get("location") or ""
                        vacancies = item.get("Vacancies")

                        description_parts = []
                        if location:
                            description_parts.append(f"Location: {location}")
                        if vacancies:
                            description_parts.append(f"Vacancies: {vacancies}")
                        if desc:
                            description_parts.append(desc.strip())

                        full_desc = " | ".join(description_parts)[:600]

                        all_jobs.append({
                            "title": self._clean_text(title),
                            "organization": self._clean_text(company),
                            "url": url,
                            "deadline": self._clean_text(deadline) if deadline else None,
                            "description": full_desc,
                            "raw_html": str(item)[:1500],
                            "source": "BDJOBS",
                            "source_type": "job_portal",
                        })
            except Exception as e:
                logger.warning(f"Bdjobs API search failed for keyword '{keyword}': {e}")

        # Step 2: Fallback to HTML scraping if API returned nothing
        if not all_jobs:
            logger.info("Bdjobs API returned 0 jobs, trying HTML fallback...")
            all_jobs = self._scrape_html_fallback()

        logger.info(f"Total verified jobs extracted from bdjobs.com: {len(all_jobs)}")
        return all_jobs

    def _scrape_html_fallback(self) -> List[Dict]:
        """Fallback to HTML scraping if API is unreachable."""
        fallback_urls = [
            "https://jobs.bdjobs.com/jobsearch.asp?fcatId=2",
            "https://jobs.bdjobs.com/jobsearch.asp?fcatId=8",
        ]
        jobs = []
        for url in fallback_urls:
            html = self.fetch(url)
            if html:
                parsed = self.parse(html, {"career_url": url})
                jobs.extend(parsed)
        return jobs

    def parse(self, html: str, source_config: dict) -> List[Dict]:
        """Parse bdjobs.com search results page."""
        soup = BeautifulSoup(html, "html5lib")
        base_url = source_config.get("career_url", "https://jobs.bdjobs.com")
        jobs = []

        # Find any job links in HTML
        for link in soup.find_all("a", href=re.compile(r"jobdetails|JobId|job_id|details", re.I)):
            title = link.get_text(strip=True)
            href = link.get("href", "")

            if not title or len(title) < 4:
                continue

            url = self.make_absolute_url(base_url, href)
            parent_text = link.parent.get_text(" ", strip=True) if link.parent else ""

            if self._is_banking_related(title, parent_text):
                jobs.append({
                    "title": self._clean_text(title),
                    "organization": "Via bdjobs.com",
                    "url": url,
                    "deadline": None,
                    "description": parent_text[:500],
                    "raw_html": str(link.parent)[:1500] if link.parent else str(link),
                    "source": "BDJOBS",
                    "source_type": "job_portal",
                })

        return jobs

    def _is_banking_related(self, title: str, company: str) -> bool:
        """Check if a job listing is related to banking/finance."""
        combined = f"{title} {company}".lower()
        return any(kw in combined for kw in self.BANKING_KEYWORDS)

    def _clean_text(self, text: Optional[str]) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()
