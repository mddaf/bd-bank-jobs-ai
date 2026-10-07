"""
Date Parser & Deadline Validator
=================================
Parses deadline strings commonly found on Bangladesh bank and job portal sites
and checks whether the deadline has passed.
Supports Bengali digits, Bengali month names, ordinals (1st, 2nd, 3rd, 18th),
2-digit and 4-digit years, and embedded timestamps.
"""

import re
import logging
from datetime import datetime, date
from typing import Optional, List

logger = logging.getLogger(__name__)

# Bengali numeral mapping
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

MONTH_NAMES = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
    # Bengali month names
    "জানুয়ারি": 1, "জানুয়ারি": 1,
    "ফেব্রুয়ারি": 2, "ফেব্রুয়ারি": 2,
    "মার্চ": 3,
    "এপ্রিল": 4,
    "মে": 5,
    "জুন": 6,
    "জুলাই": 7,
    "আগস্ট": 8, "আগষ্ট": 8,
    "সেপ্টেম্বর": 9,
    "অক্টোবর": 10,
    "নভেম্বর": 11,
    "ডিসেম্বর": 12,
}


def extract_all_dates(text: Optional[str]) -> List[date]:
    """
    Find and return all valid dates found in the given text string.
    Uses negative lookaround (?<!\\d) instead of \\b to reliably match
    dates glued to words (e.g. Program2019-09-26).
    """
    if not text:
        return []

    s = str(text).strip().translate(BN_DIGITS)
    found_dates = []

    # 1. YYYY-MM-DD or YYYY/MM/DD or YYYY.MM.DD
    for m in re.finditer(r'(?<!\d)(20\d\d)[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])(?!\d)', s):
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            found_dates.append(d)
        except ValueError:
            pass

    # 2. DD-MM-YYYY or DD/MM/YYYY or DD.MM.YYYY
    for m in re.finditer(r'(?<!\d)(0?[1-9]|[12]\d|3[01])[-/.](0?[1-9]|1[0-2])[-/.](20\d\d)(?!\d)', s):
        try:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            found_dates.append(d)
        except ValueError:
            pass

    # 3. YY-MM-DD (e.g. 19-08-27, 21-12-01) where YY is past year (15-25)
    for m in re.finditer(r'(?<!\d)(1[5-9]|2[0-5])[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])(?!\d)', s):
        try:
            yr = 2000 + int(m.group(1))
            d = date(yr, int(m.group(2)), int(m.group(3)))
            found_dates.append(d)
        except ValueError:
            pass

    # 4. DD [th/st/nd/rd] Month YYYY (e.g., 25th Oct 2026, 18 October 2026, ১৮ অক্টোবর ২০২৬)
    for m in re.finditer(r'(?<!\d)(0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?\s+([A-Za-z\u0980-\u09FF]+),?\s+(20\d\d)(?!\d)', s):
        month_str = m.group(2).lower()
        if month_str in MONTH_NAMES:
            try:
                d = date(int(m.group(3)), MONTH_NAMES[month_str], int(m.group(1)))
                found_dates.append(d)
            except ValueError:
                pass

    # 5. Month DD [th/st/nd/rd], YYYY (e.g., October 25, 2026 or May 15, 2024)
    for m in re.finditer(r'(?<!\d)([A-Za-z\u0980-\u09FF]+)\s+(0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?,?\s+(20\d\d)(?!\d)', s):
        month_str = m.group(1).lower()
        if month_str in MONTH_NAMES:
            try:
                d = date(int(m.group(3)), MONTH_NAMES[month_str], int(m.group(2)))
                found_dates.append(d)
            except ValueError:
                pass

    return found_dates


def parse_deadline(raw_deadline: Optional[str]) -> Optional[date]:
    """
    Attempt to parse a date object from a deadline string.
    If multiple dates are present (e.g. start date and end date),
    returns the latest date (the deadline).
    """
    if not raw_deadline:
        return None

    dates = extract_all_dates(str(raw_deadline))
    if dates:
        return max(dates)

    return None


def is_deadline_passed(raw_deadline: Optional[str], target_date: Optional[date] = None) -> bool:
    """
    Check if the deadline has passed.
    Returns True if deadline is identified and is strictly earlier than target_date (default: today).
    Returns False if deadline is today or in the future, or cannot be parsed.
    """
    if not raw_deadline:
        return False

    parsed = parse_deadline(raw_deadline)
    if not parsed:
        return False

    today = target_date or date.today()
    return parsed < today


def is_job_expired(job_data: dict, target_date: Optional[date] = None) -> bool:
    """
    Comprehensive deadline & expiry check for a job posting.
    Checks:
      1. raw deadline field
      2. title text
      3. description
      4. url (e.g. path timestamps like /2021/04/)
    
    Returns True if:
      - Any parsed deadline is strictly earlier than target_date (default: today).
      - Text/URL explicitly references past years (2015-2025) and has NO valid current/future date (>= 2026).
    Returns False if active or if no past expiration evidence exists.
    """
    today = target_date or date.today()

    dl_field = job_data.get("deadline")
    title = job_data.get("title", "")
    desc = job_data.get("description", "")
    url = job_data.get("url", "")

    # Collect all dates mentioned anywhere across the job metadata
    all_dates = []
    if dl_field:
        all_dates.extend(extract_all_dates(str(dl_field)))
    if title:
        all_dates.extend(extract_all_dates(str(title)))
    if desc:
        all_dates.extend(extract_all_dates(str(desc)))
    if url:
        all_dates.extend(extract_all_dates(str(url)))

    if all_dates:
        latest_date = max(all_dates)
        if latest_date < today:
            logger.info(f"Job is expired: latest date {latest_date} < today {today} (Title: '{title[:40]}')")
            return True
        else:
            return False

    # Check for obsolete past year stamps (2015-2025) in URL or text
    combined_str = f"{url} {title} {dl_field} {desc}".lower()
    past_years = re.findall(r'(?<!\d)(201[5-9]|202[0-5])(?!\d)', combined_str)
    future_years = re.findall(r'(?<!\d)(202[6-9]|203\d)(?!\d)', combined_str)

    if past_years and not future_years:
        logger.info(f"Job contains obsolete past year {past_years[0]} with no future date. Flagged expired: '{title[:40]}'")
        return True

    return False
