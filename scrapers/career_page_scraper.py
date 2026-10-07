"""
Career Page Scraper
=====================
Scrapes direct career/job pages from bank and financial institution websites.
Uses BeautifulSoup with strict validation to prevent false positives (governance,
board members, navigation links) and ensure working links.
"""

import re
import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class CareerPageScraper(BaseScraper):
    """
    Scraper for direct bank and financial institution career pages.
    """

    # Real job role keywords that denote an actual employment opening
    JOB_ROLE_KEYWORDS = [
        "officer", "manager", "executive", "analyst", "teller",
        "assistant", "specialist", "trainee", "associate", "intern",
        "lead", "head of", "developer", "engineer", "clerk", "operator",
        "cashier", "advisor", "consultant", "supervisor", "representative",
        "নিয়োগ", "বিজ্ঞপ্তি", "পদ", "কর্মকর্তা", "সহকারী", "ব্যবস্থাপক",
    ]

    # Strictest exclusion keywords: NEVER treat these as jobs
    STRICT_EXCLUDE_KEYWORDS = [
        # Governance & Management
        "board of director", "board of directors", "board member",
        "managing director", "chief executive officer", "managing director & ceo",
        "managing director's", "md & ceo", "md's speech",
        "chairman", "chairman's message", "vice chairman", "executive committee",
        "audit committee", "risk management committee", "nomination and remuneration",
        "shariah supervisory", "shariah council", "independent director",
        "shareholding director", "sponsor director", "management committee",
        "senior management", "organogram", "code of conduct", "code of ethics",
        "citizen charter", "whistle blower", "corporate governance",
        # Generic corporate pages & compliance directories (personal contacts)
        "annual report", "financial statement", "quarterly report", "balance sheet",
        "investor relation", "csr activities", "csr", "press release", "news & event",
        "news & events", "tender", "procurement", "e-tender", "auction",
        "schedule of charges", "interest rate", "exchange rate", "foreign exchange",
        "branch locator", "atm locator", "agent banking", "sub-branch",
        "privacy policy", "terms of use", "terms & conditions", "disclaimer",
        "cookie policy", "sitemap", "site map", "faq", "frequently asked questions",
        "about us", "who we are", "contact us", "feedback", "complaint",
        "information officer", "information officers", "designated officer", "rti officer",
        "grs officer", "grievance redress", "focal point officer", "focal point",
        "complaint officer", "right to information", "তথ্য কর্মকর্তা", "দায়িত্বপ্রাপ্ত কর্মকর্তা",
        "অভিযোগ প্রতিকার", "সেবা প্রদান প্রতিশ্রুতি", "অভিযোগ নিষ্পত্তি কর্মকর্তা", "আপিল কর্মকর্তা",
        "আপিল কর্মকর্তাগণ", "information right officer", "auditor and legal advisor",
        "talk to an advisor", "talk to us", "lead generation", "agent lead generation",
        # Exam results, appointment letters, past recruitment results
        "selected candidate", "selected candidates", "appointment letter", "joining date",
        "written test result", "viva-voce", "viva voce", "admit card", "seat plan",
        "exam result", "recruitment result", "final result", "shortlisted candidates",
        "চূড়ান্ত ফলাফল", "লিখিত পরীক্ষার ফলাফল", "মৌখিক পরীক্ষা", "নিয়োগের ফলাফল",
        # Banking products & loans
        "loan against", "loan product", "credit card", "deposit scheme", "pension vata",
        "নিরাপদ অর্জন", "পদ্মা মৌসুম", "পদ্মাবতী", "সঞ্চয় প্রকল্প", "আমানত",
        # Generic buttons/headings that are not specific job titles
        "career", "careers", "career opportunity", "career opportunities",
        "current opening", "current openings", "current vacancies", "vacancies",
        "job opening", "job openings", "jobs", "job opportunity",
        "join us", "work with us", "apply now", "view details", "read more",
        "click here", "see more", "download", "download circular", "apply online",
    ]

    def parse(self, html: str, source_config: dict) -> list:
        """Parse career page HTML and extract genuine job postings."""
        from utils.date_parser import is_job_expired

        soup = BeautifulSoup(html, "html.parser")
        base_url = source_config.get("career_url", "")
        org_name = source_config.get("name", "Unknown")
        scrape_cfg = source_config.get("scrape_config", {})

        jobs = []

        # Strategy 1: Configured selectors
        jobs = self._parse_with_selectors(soup, scrape_cfg, base_url, org_name, source_config)

        # Strategy 2: Structured fallback if configured selectors found nothing
        if not jobs:
            logger.debug(f"Configured selectors found nothing for {org_name}, trying auto-detection...")
            jobs = self._auto_detect_jobs(soup, base_url, org_name, source_config)

        # Deduplicate and validate
        seen_urls = set()
        seen_titles = set()
        valid_jobs = []

        for job in jobs:
            clean_title = job["title"].lower().strip()
            clean_url = job["url"].strip()

            if clean_url in seen_urls or clean_title in seen_titles:
                continue

            # Drop expired postings right at scrape time
            if is_job_expired(job):
                logger.info(f"Dropped expired job at scrape time: '{job['title']}' @ {job['organization']}")
                continue

            seen_urls.add(clean_url)
            seen_titles.add(clean_title)
            valid_jobs.append(job)

        return valid_jobs

    def _is_legitimate_job_title(self, title: str) -> bool:
        """
        Strict check to confirm this string is an actual job position,
        not a person's name, corporate committee, product, or navigation header.
        """
        if not title or len(title) < 6:
            return False

        # Reject pure URLs, numbers, or emails
        if title.startswith("http") or title.isdigit() or "@" in title:
            return False

        t_lower = title.lower()

        # Check against strict exclusions
        for exclude in self.STRICT_EXCLUDE_KEYWORDS:
            if exclude in t_lower:
                return False

        # Additional product/service/governance exclusions
        extra_excludes = [
            "committee", "supervisory", "council", "internet banking", "family remit",
            "medi remit", "edu remit", "remittance", "locator", "head office",
            "deposit", "account", "fund transfer", "customer care", "bftn", "rtgs",
        ]
        for ex in extra_excludes:
            if ex in t_lower:
                return False

        # Must have at least one job role keyword matching WHOLE word boundaries
        for role in self.JOB_ROLE_KEYWORDS:
            if re.search(r'\b' + re.escape(role) + r'\b', t_lower):
                return True

        return False

    def _clean_and_validate_url(self, raw_url: str, base_url: str) -> str:
        """Validate URL to ensure it is clickable, absolute, and not broken."""
        if not raw_url:
            return base_url

        raw_url = raw_url.strip()

        # Reject useless javascript or hash links
        if raw_url.startswith(("javascript:void", "javascript:;", "javascript:void(0)")):
            return base_url
        if raw_url == "#" or raw_url.endswith("/#") or raw_url.endswith("#"):
            return base_url

        # Check if it's a javascript showpdf link
        pdf_match = re.search(r'showpdf\("([^"]+)"', raw_url, re.IGNORECASE)
        if pdf_match:
            return urljoin(base_url, pdf_match.group(1).replace("../", ""))

        # Convert to absolute URL
        absolute = urljoin(base_url, raw_url)
        parsed = urlparse(absolute)

        # Must have valid scheme and network location
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return base_url

        # Reject if URL points directly to homepage root
        if parsed.path in ("", "/") and not parsed.query:
            return base_url

        return absolute

    def _parse_with_selectors(self, soup: BeautifulSoup, scrape_cfg: dict,
                               base_url: str, org_name: str, source_config: dict) -> list:
        """Parse using configured CSS selectors."""
        jobs = []
        container_selector = scrape_cfg.get("job_container", "")
        if not container_selector:
            return jobs

        containers = []
        for selector in container_selector.split(","):
            selector = selector.strip()
            if selector:
                try:
                    found = soup.select(selector)
                    containers.extend(found)
                except Exception:
                    continue

        for container in containers:
            job = self._extract_job_from_element(
                container, scrape_cfg, base_url, org_name, source_config
            )
            if job:
                jobs.append(job)

        return jobs

    def _extract_job_from_element(self, element, scrape_cfg: dict,
                                   base_url: str, org_name: str, source_config: dict) -> dict:
        """Extract job details from a single HTML element."""
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

        if not title:
            title = element.get_text(strip=True)

        title = self._clean_text(title)
        if not self._is_legitimate_job_title(title):
            return None

        # Extract link
        raw_href = ""
        link_el = element.select_one("a[href]")
        if link_el:
            raw_href = link_el.get("href", "")
        elif element.name == "a" and element.get("href"):
            raw_href = element["href"]

        url = self._clean_and_validate_url(raw_href, base_url)

        # Extract deadline
        deadline = None
        deadline_selectors = scrape_cfg.get("deadline_selector", "").split(",")
        for sel in deadline_selectors:
            sel = sel.strip()
            if sel:
                deadline_el = element.select_one(sel)
                if deadline_el:
                    deadline_text = self._clean_text(deadline_el.get_text(strip=True))
                    if deadline_text:
                        deadline = deadline_text
                        break

        if not deadline:
            deadline = self._find_nearby_deadline(element)

        desc = self._clean_text(element.get_text(" ", strip=True))[:500]

        return {
            "title": title,
            "organization": org_name,
            "url": url,
            "deadline": deadline,
            "description": desc,
            "raw_html": str(element)[:2000],
            "source": source_config.get("short_name", "UNKNOWN"),
            "source_type": source_config.get("type", "unknown"),
        }

    def _auto_detect_jobs(self, soup: BeautifulSoup, base_url: str,
                           org_name: str, source_config: dict) -> list:
        """
        Auto-detection fallback: search for links and cards that match
        strict job role criteria.
        """
        jobs = []

        # Check links
        for link in soup.find_all("a", href=True):
            text = self._clean_text(link.get_text(strip=True))
            href = link.get("href", "")

            if not self._is_legitimate_job_title(text):
                continue

            url = self._clean_and_validate_url(href, base_url)
            deadline = self._find_nearby_deadline(link)

            jobs.append({
                "title": text,
                "organization": org_name,
                "url": url,
                "deadline": deadline,
                "description": f"Position: {text} at {org_name}",
                "raw_html": str(link.parent)[:2000] if link.parent else str(link),
                "source": source_config.get("short_name", "UNKNOWN"),
                "source_type": source_config.get("type", "unknown"),
            })

        # Check table rows
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) >= 2:
                title_cand = self._clean_text(tds[0].get_text(strip=True))
                if self._is_legitimate_job_title(title_cand):
                    link_el = tr.find("a", href=True)
                    href = link_el.get("href", "") if link_el else ""
                    url = self._clean_and_validate_url(href, base_url)
                    deadline = self._find_nearby_deadline(tr)

                    jobs.append({
                        "title": title_cand,
                        "organization": org_name,
                        "url": url,
                        "deadline": deadline,
                        "description": self._clean_text(tr.get_text(" ", strip=True))[:500],
                        "raw_html": str(tr)[:2000],
                        "source": source_config.get("short_name", "UNKNOWN"),
                        "source_type": source_config.get("type", "unknown"),
                    })

        return jobs

    def _find_nearby_deadline(self, element) -> str:
        """Find deadline date pattern near the given element."""
        date_pattern = re.compile(
            r'\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}'
            r'|\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{2,4}'
            r'|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2},?\s+\d{2,4}',
            re.IGNORECASE
        )

        for sibling in element.find_next_siblings(limit=3):
            text = sibling.get_text(strip=True)
            match = date_pattern.search(text)
            if match:
                return match.group()

        if element.parent:
            text = element.parent.get_text(strip=True)
            match = date_pattern.search(text)
            if match:
                return match.group()

        return None

    def _clean_text(self, text: str) -> str:
        """Clean extra whitespace and control chars."""
        if not text:
            return ""
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    def scrape_all_concurrent(self, sources: list, max_workers: int = 15) -> list:
        """
        Scrape all bank and financial institution career pages in parallel.
        Processes 100+ institutions in under 15-20 seconds.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        all_jobs = []

        def _scrape_single(cfg):
            try:
                return self.scrape(cfg)
            except Exception as e:
                logger.debug(f"Error scraping {cfg.get('name')}: {e}")
                return []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_scrape_single, s): s for s in sources}
            for fut in as_completed(futures):
                try:
                    res = fut.result()
                    if res:
                        all_jobs.extend(res)
                except Exception:
                    pass

        return all_jobs
