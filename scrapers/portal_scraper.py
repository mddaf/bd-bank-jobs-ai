"""
Job Portal & Media Aggregator Scraper
======================================
Scrapes bank & financial job openings from:
  1. LinkedIn BD Bank Jobs (Public Guest API)
  2. BDJobsToday (Bank/Finance/Insurance Category)
  3. Chakrir Khobor (Bank Jobs Tag / Circular Media)
  4. Skill Jobs (Banking & Finance Openings)
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


class PortalScraper(BaseScraper):
    """
    Unified scraper for modern job portals and newspaper/circular aggregators.
    Extracts structured bank circulars from LinkedIn, BDJobsToday, Chakrir Khobor, and Skill Jobs.
    """

    CHROME_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    BANK_NAME_PATTERNS = [
        (r"(?i)bangladesh\s+bank", "Bangladesh Bank"),
        (r"(?i)sonali\s+bank", "Sonali Bank PLC"),
        (r"(?i)janata\s+bank", "Janata Bank PLC"),
        (r"(?i)agrani\s+bank", "Agrani Bank PLC"),
        (r"(?i)rupali\s+bank", "Rupali Bank PLC"),
        (r"(?i)brac\s+bank", "BRAC Bank PLC"),
        (r"(?i)city\s+bank", "City Bank PLC"),
        (r"(?i)dutch\s*[-]?\s*bangla\s+bank|dbbl", "Dutch-Bangla Bank (DBBL)"),
        (r"(?i)eastern\s+bank|ebl", "Eastern Bank PLC (EBL)"),
        (r"(?i)islamic?\s+bank|ibbl", "Islami Bank Bangladesh PLC"),
        (r"(?i)pubali\s+bank", "Pubali Bank PLC"),
        (r"(?i)palli\s+sanchay\s+bank", "Palli Sanchay Bank"),
        (r"(?i)karmasangsthan\s+bank", "Karmasangsthan Bank"),
        (r"(?i)probashi\s+kallyan\s+bank", "Probashi Kallyan Bank"),
        (r"(?i)krishi\s+bank|bkbl", "Bangladesh Krishi Bank"),
        (r"(?i)rajshahi\s+krishi", "Rajshahi Krishi Unnayan Bank"),
        (r"(?i)midland\s+bank", "Midland Bank PLC"),
        (r"(?i)meghna\s+bank", "Meghna Bank PLC"),
        (r"(?i)mercantile\s+bank|mbl", "Mercantile Bank PLC"),
        (r"(?i)mutual\s+trust\s+bank|mtb", "Mutual Trust Bank PLC"),
        (r"(?i)national\s+bank", "National Bank Limited"),
        (r"(?i)nrb\s+bank", "NRB Bank PLC"),
        (r"(?i)prime\s+bank", "Prime Bank PLC"),
        (r"(?i)southeast\s+bank", "Southeast Bank PLC"),
        (r"(?i)standard\s+chartered", "Standard Chartered Bangladesh"),
        (r"(?i)hsbc", "HSBC Bangladesh"),
        (r"(?i)icb\s+asset|icb", "Investment Corporation of Bangladesh (ICB)"),
        (r"(?i)idlc", "IDLC Finance PLC"),
        (r"(?i)ipdc", "IPDC Finance PLC"),
        (r"(?i)lanka\s*bangla", "LankaBangla Finance PLC"),
        (r"(?i)bankers\s+selection\s+committee|bscs", "Bankers' Selection Committee (BSCS)"),
    ]

    def scrape_all_portals(self) -> List[Dict]:
        """
        Scrape all 4 auxiliary portals and aggregators:
          - LinkedIn BD Bank Jobs
          - BDJobsToday
          - Chakrir Khobor
          - Skill Jobs
        """
        all_jobs = []
        logger.info("Starting auxiliary portal scraping across LinkedIn, BDJobsToday, Chakrir Khobor, and Skill Jobs...")

        # 1. LinkedIn BD
        try:
            li_jobs = self.scrape_linkedin()
            all_jobs.extend(li_jobs)
            logger.info(f"  [LinkedIn BD] Extracted {len(li_jobs)} banking circulars")
        except Exception as e:
            logger.error(f"  [LinkedIn BD] Scrape failed: {e}")

        # 2. BDJobsToday
        try:
            bjt_jobs = self.scrape_bdjobstoday()
            all_jobs.extend(bjt_jobs)
            logger.info(f"  [BDJobsToday] Extracted {len(bjt_jobs)} bank & finance circulars")
        except Exception as e:
            logger.error(f"  [BDJobsToday] Scrape failed: {e}")

        # 3. Chakrir Khobor
        try:
            ck_jobs = self.scrape_chakrir_khobor()
            all_jobs.extend(ck_jobs)
            logger.info(f"  [Chakrir Khobor] Extracted {len(ck_jobs)} bank circular posts")
        except Exception as e:
            logger.error(f"  [Chakrir Khobor] Scrape failed: {e}")

        # 4. Skill Jobs
        try:
            sj_jobs = self.scrape_skilljobs()
            all_jobs.extend(sj_jobs)
            logger.info(f"  [Skill Jobs] Extracted {len(sj_jobs)} finance & banking openings")
        except Exception as e:
            logger.error(f"  [Skill Jobs] Scrape failed: {e}")

        logger.info(f"Total jobs collected from all 4 auxiliary portals: {len(all_jobs)}")
        return all_jobs

    def scrape_by_source_shortname(self, short_name: str) -> List[Dict]:
        """Scrape a specific portal by its short name."""
        sn = short_name.upper()
        if sn == "LINKEDIN_BD":
            return self.scrape_linkedin()
        elif sn == "BDJOBSTODAY":
            return self.scrape_bdjobstoday()
        elif sn == "CHAKRIR_KHOBOR":
            return self.scrape_chakrir_khobor()
        elif sn == "SKILL_JOBS":
            return self.scrape_skilljobs()
        return []

    # ================================================================
    # 1. LinkedIn Bangladesh Bank Jobs
    # ================================================================
    def scrape_linkedin(self) -> List[Dict]:
        """Scrape LinkedIn public guest jobs API for Bangladesh banking posts."""
        endpoints = [
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=bank&location=Bangladesh&geoId=106215326",
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=finance&location=Bangladesh&geoId=106215326",
        ]
        jobs = []
        seen_urls = set()

        for url in endpoints:
            try:
                resp = self.session.get(url, headers=self.CHROME_HEADERS, timeout=10, verify=False)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select("div.base-card, li.base-card")

                for card in cards:
                    title_el = card.select_one(".base-search-card__title")
                    comp_el = card.select_one(".base-search-card__subtitle")
                    link_el = card.select_one("a.base-card__full-link, a")
                    loc_el = card.select_one(".job-search-card__location")
                    time_el = card.select_one("time")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = comp_el.get_text(strip=True) if comp_el else "Financial Institution"
                    raw_href = link_el.get("href", "") if link_el else ""
                    location = loc_el.get_text(strip=True) if loc_el else "Bangladesh"
                    date_posted = time_el.get_text(strip=True) if time_el else ""

                    if not title or len(title) < 3 or not raw_href:
                        continue

                    # Strip tracking parameters from LinkedIn job URL
                    job_url = raw_href.split("?")[0].strip()
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    # Relevance check
                    combined = f"{title} {company}".lower()
                    if not any(k in combined for k in ["bank", "banking", "finance", "financial", "credit", "audit", "treasury", "risk"]):
                        continue

                    desc = f"Location: {location}"
                    if date_posted:
                        desc += f" | Posted: {date_posted}"

                    jobs.append({
                        "title": self._clean_text(title),
                        "organization": self._clean_text(company),
                        "url": job_url,
                        "deadline": None,
                        "description": desc,
                        "raw_html": str(card)[:1500],
                        "source": "LINKEDIN_BD",
                        "source_type": "job_portal",
                    })
            except Exception as e:
                logger.warning(f"Error scraping LinkedIn URL {url}: {e}")

        return jobs

    # ================================================================
    # 2. BDJobsToday (Bank/Finance Category)
    # ================================================================
    def scrape_bdjobstoday(self) -> List[Dict]:
        """Scrape BDJobsToday newspaper & official cutout circulars."""
        url = "https://bdjobstoday.com/jobs.php?cat=3&cat_name=Bank/Finance/Insurance"
        jobs = []
        seen_urls = set()

        try:
            resp = self.session.get(url, headers=self.CHROME_HEADERS, timeout=12, verify=False)
            if resp.status_code != 200:
                return jobs

            soup = BeautifulSoup(resp.text, "html.parser")
            tables = soup.find_all("table", class_="list")

            for tbl in tables:
                title_link = tbl.select_one("a.link02, a[href*='job_details.php']")
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                href = title_link.get("href", "")
                if not title or not href:
                    continue

                full_url = href if href.startswith("http") else f"https://bdjobstoday.com/{href.lstrip('./').lstrip('../')}"
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                comp_el = tbl.select_one(".HotJobsCompany")
                company = comp_el.get_text(strip=True) if comp_el else "Bank/Financial Institution"

                # Parse deadline
                deadline = None
                deadline_match = re.search(r"Deadline:\s*([0-9]{1,2}\s+[A-Za-z]+,?\s+[0-9]{4})", tbl.get_text())
                if deadline_match:
                    deadline = deadline_match.group(1).strip()

                # Parse education and experience
                edu_el = tbl.select_one("span.detailsnoncap")
                education = edu_el.get_text(strip=True) if edu_el else ""

                desc = f"Education: {education}" if education else "Bank & Financial Institution Circular"

                jobs.append({
                    "title": self._clean_text(title),
                    "organization": self._clean_text(company),
                    "url": full_url,
                    "deadline": deadline,
                    "description": desc,
                    "raw_html": str(tbl)[:1500],
                    "source": "BDJOBSTODAY",
                    "source_type": "image_aggregator",
                })
        except Exception as e:
            logger.warning(f"Error scraping BDJobsToday: {e}")

        return jobs

    # ================================================================
    # 3. Chakrir Khobor (Bank Jobs Tag)
    # ================================================================
    def scrape_chakrir_khobor(self) -> List[Dict]:
        """Scrape Chakrir Khobor newspaper bank circular cutouts."""
        url = "https://chakrirkhobor.com.bd/tag/bank-jobs/"
        jobs = []
        seen_urls = set()

        try:
            resp = self.session.get(url, headers=self.CHROME_HEADERS, timeout=12, verify=False)
            if resp.status_code != 200:
                return jobs

            soup = BeautifulSoup(resp.text, "html.parser")
            articles = soup.select("article, div.post")

            for art in articles:
                # Find anchor tag with non-empty text (skipping thumbnail link)
                title = ""
                href = ""
                for a_tag in art.find_all("a"):
                    txt = a_tag.get_text(strip=True)
                    if len(txt) > 3:
                        title = txt
                        href = a_tag.get("href", "")
                        break

                if not title or not href:
                    continue

                if href in seen_urls:
                    continue
                seen_urls.add(href)

                # Exclude question solves, exam results, tips, suggestions
                low_title = title.lower()
                if any(bad in low_title for bad in ["question solve", "question solution", "tips", "suggestion", "result", "ফলাফল", "প্রশ্ন সমাধান", "পরামর্শ", "সাজেশন", "রোল"]):
                    continue

                # Determine company/organization name
                company = self._infer_bank_from_title(title)

                # Check for image
                img_el = art.select_one("img")
                img_url = img_el.get("src", "") if img_el else ""

                desc_parts = [f"Circular Post: {title}"]
                if img_url:
                    desc_parts.append(f"Image: {img_url}")

                jobs.append({
                    "title": self._clean_text(title),
                    "organization": self._clean_text(company),
                    "url": href,
                    "deadline": None,
                    "description": " | ".join(desc_parts)[:500],
                    "raw_html": str(art)[:1500],
                    "source": "CHAKRIR_KHOBOR",
                    "source_type": "image_aggregator",
                })
        except Exception as e:
            logger.warning(f"Error scraping Chakrir Khobor: {e}")

        return jobs

    # ================================================================
    # 4. Skill Jobs (Browse Jobs Search)
    # ================================================================
    def scrape_skilljobs(self) -> List[Dict]:
        """Scrape Skill Jobs for banking & finance openings."""
        queries = [
            "https://skill.jobs/browse-jobs?search=bank",
            "https://skill.jobs/browse-jobs?search=finance",
        ]
        jobs = []
        seen_urls = set()

        for url in queries:
            try:
                resp = self.session.get(url, headers=self.CHROME_HEADERS, timeout=10, verify=False)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                links = soup.find_all("a", href=lambda h: h and "/jobs/" in h)

                for link in links:
                    href = link.get("href", "")
                    full_url = href if href.startswith("http") else f"https://skill.jobs{href}"
                    if full_url in seen_urls:
                        continue

                    raw_text = link.get_text(" ", strip=True)
                    if not raw_text or len(raw_text) < 4:
                        continue

                    # Split title and company using em-dash or en-dash (\u2014, \u2013)
                    parts = re.split(r"[\u2014\u2013]", raw_text)
                    if len(parts) >= 2:
                        title = parts[0].strip()
                        comp_and_loc = parts[1].strip()
                        comp_parts = comp_and_loc.split(",")
                        company = comp_parts[0].strip()
                        location = ", ".join(comp_parts[1:]).strip() if len(comp_parts) > 1 else ""
                    else:
                        title = raw_text
                        company = "Financial Enterprise"
                        location = ""

                    # Verify banking relevance
                    comb = f"{title} {company}".lower()
                    if not any(k in comb for k in ["bank", "banking", "finance", "financial", "credit", "audit", "treasury", "fundraising", "fin"]):
                        continue

                    seen_urls.add(full_url)

                    jobs.append({
                        "title": self._clean_text(title),
                        "organization": self._clean_text(company),
                        "url": full_url,
                        "deadline": None,
                        "description": f"Location: {location}" if location else "Skill Jobs Opportunity",
                        "raw_html": str(link.parent)[:1500] if link.parent else str(link),
                        "source": "SKILL_JOBS",
                        "source_type": "job_portal",
                    })
            except Exception as e:
                logger.warning(f"Error scraping Skill Jobs query {url}: {e}")

        return jobs

    def parse(self, html: str, source_config: dict) -> List[Dict]:
        """Standard parser implementation required by BaseScraper."""
        return []

    def _infer_bank_from_title(self, text: str) -> str:
        """Infer bank or institution name from Bengali/English title text."""
        for pattern, bank_name in self.BANK_NAME_PATTERNS:
            if re.search(pattern, text):
                return bank_name

        # Bengali bank keyword checks
        if "বাংলাদেশ ব্যাংক" in text:
            return "Bangladesh Bank"
        if "কর্মসংস্থান" in text:
            return "Karmasangsthan Bank"
        if "পল্লী সঞ্চয়" in text or "পল্লী সঞ্চয়" in text:
            return "Palli Sanchay Bank"
        if "পূবালী" in text:
            return "Pubali Bank PLC"
        if "সোনালী" in text:
            return "Sonali Bank PLC"
        if "জনতা" in text:
            return "Janata Bank PLC"
        if "অগ্রণী" in text:
            return "Agrani Bank PLC"
        if "রূপালী" in text or "রুপালী" in text:
            return "Rupali Bank PLC"
        if "ব্যাংক" in text:
            return "Bank / Financial Institution"

        return "Government / Bank Recruitment"

    def _clean_text(self, text: Optional[str]) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        text = re.sub(r"[\r\n\t]+", " ", text)
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()
