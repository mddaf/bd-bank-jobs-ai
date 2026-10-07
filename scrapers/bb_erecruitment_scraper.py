"""
Bangladesh Bank e-Recruitment Scraper (BSCS)
=============================================
Scrapes official circulars published by Bangladesh Bank's
Bankers' Selection Committee Secretariat (BSCS), which manages
centralized recruitment for all State-Owned and Specialized banks in Bangladesh:
  - Sonali Bank PLC
  - Janata Bank PLC
  - Agrani Bank PLC
  - Rupali Bank PLC
  - BASIC Bank Limited
  - Bangladesh Krishi Bank (BKB)
  - Rajshahi Krishi Unnayan Bank (RAKUB)
  - Karmasangsthan Bank
  - Probashi Kollyan Bank (PKB)
  - Ansar-VDP Unnayan Bank
  - Bangladesh Development Bank PLC (BDBL)
"""

import re
import logging
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class BBErecruitmentScraper(BaseScraper):
    """
    Dedicated scraper for Bangladesh Bank's central recruitment portal.
    URL: https://erecruitment.bb.org.bd/onlineapp/joblist.php
    """

    TARGET_URL = "https://erecruitment.bb.org.bd/onlineapp/joblist.php"

    def scrape_jobs(self) -> list:
        """Fetch and parse all active job circulars from BB e-Recruitment."""
        import requests
        import urllib3
        urllib3.disable_warnings()

        source_config = {
            "name": "Bangladesh Bank (BSCS Central Recruitment)",
            "short_name": "BB_BSCS",
            "type": "state_owned",
            "career_url": self.TARGET_URL,
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            r = requests.get(self.TARGET_URL, headers=headers, verify=False, timeout=12)
            if r.status_code != 200:
                logger.error(f"BB e-Recruitment returned HTTP {r.status_code}")
                return []
            return self.parse(r.text, source_config)
        except Exception as e:
            logger.error(f"Failed to fetch Bangladesh Bank e-Recruitment page: {e}")
            return []

    def parse(self, html: str, source_config: dict) -> list:
        """Parse the HTML table of jobs from BB e-Recruitment."""
        soup = BeautifulSoup(html, "html.parser")
        jobs = []

        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 8:
                continue

            job_id = tds[0].get_text(strip=True)
            if not job_id.isdigit():
                continue

            raw_position = tds[1].get_text(" ", strip=True)
            # Clean up "[View Circular]" button text
            position = re.sub(r'\[\s*View\s*Circular\s*\]', '', raw_position, flags=re.IGNORECASE).strip()
            # Clean multiple spaces
            position = re.sub(r'\s{2,}', ' ', position)

            # Extract circular PDF link if present
            pdf_link = None
            for a in tds[1].find_all("a", href=True):
                href = a.get("href", "")
                pdf_match = re.search(r'showpdf\("([^"]+)"', href)
                if pdf_match:
                    pdf_rel = pdf_match.group(1).replace("../", "")
                    pdf_link = f"https://erecruitment.bb.org.bd/{pdf_rel}"
                    break
                elif href.endswith(".pdf"):
                    pdf_link = self.make_absolute_url("https://erecruitment.bb.org.bd/", href)
                    break

            posts_count = tds[2].get_text(strip=True)
            salary = tds[3].get_text(" ", strip=True)
            salary = re.sub(r'\s{2,}', ' ', salary)
            age_calc = tds[4].get_text(strip=True)
            edu_req = tds[5].get_text(" ", strip=True)
            edu_req = re.sub(r'\s{2,}', ' ', edu_req)
            fee = tds[6].get_text(strip=True)
            deadline = tds[7].get_text(strip=True)

            # Unique URL per job circular position
            if pdf_link:
                primary_url = f"{pdf_link}#jobid={job_id}"
            else:
                primary_url = f"https://erecruitment.bb.org.bd/onlineapp/joblist.php#jobid={job_id}"

            # Extract specific organization name from title
            org_name = "Bangladesh Bank / BSCS"
            org_match = re.search(r'(?:for|of)\s+([A-Za-z0-9\s\.\(\)\-]+Bank[A-Za-z0-9\s\.\(\)\-]*)', position, re.IGNORECASE)
            if org_match:
                extracted_org = org_match.group(1).strip()
                extracted_org = re.sub(r'[,\.\-]+$', '', extracted_org).strip()
                if len(extracted_org) > 3:
                    org_name = extracted_org

            # Construct clean description with rich details
            desc_parts = []
            if posts_count:
                desc_parts.append(f"Vacancies: {posts_count} post(s)")
            if salary:
                desc_parts.append(f"Salary Scale: {salary}")
            if edu_req:
                desc_parts.append(f"Requirements: {edu_req}")
            if fee:
                desc_parts.append(f"Application Fee: {fee}")
            if pdf_link:
                desc_parts.append(f"Circular PDF: {pdf_link}")
            desc_parts.append("Apply Portal: https://erecruitment.bb.org.bd/onlineapp/joblist.php")
            desc = " | ".join(desc_parts)

            jobs.append({
                "title": position,
                "organization": org_name,
                "url": primary_url,
                "deadline": deadline if deadline else None,
                "description": desc[:1000],
                "raw_html": str(tr)[:2000],
                "source": "BB_BSCS",
                "source_type": "state_owned",
            })

        logger.info(f"BB e-Recruitment parsed: {len(jobs)} official jobs")
        return jobs
