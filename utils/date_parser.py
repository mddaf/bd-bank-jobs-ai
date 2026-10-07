"""
Date Parser & Deadline Validator
=================================
Parses deadline strings commonly found on Bangladesh bank and job portal sites
and checks whether the deadline has passed.
"""

import re
import logging
from datetime import datetime, date
from typing import Optional

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
}


def parse_deadline(raw_deadline: Optional[str]) -> Optional[date]:
    """
    Attempt to parse a date object from a deadline string.
    Returns datetime.date if successfully parsed, None otherwise.
    """
    if not raw_deadline:
        return None

    text = str(raw_deadline).strip().translate(BN_DIGITS)

    # 1. Look for YYYY-MM-DD or YYYY/MM/DD
    m = re.search(r'\b(20\d\d)[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])\b', text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # 2. Look for DD-MM-YYYY or DD/MM/YYYY
    m = re.search(r'\b(0?[1-9]|[12]\d|3[01])[-/.](0?[1-9]|1[0-2])[-/.](20\d\d)\b', text)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass

    # 3. Look for DD Month YYYY (e.g., 25 Oct 2026, 18 October 2026)
    m = re.search(r'\b(0?[1-9]|[12]\d|3[01])\s+([A-Za-z]+)\s+(20\d\d)\b', text)
    if m:
        month_str = m.group(2).lower()
        if month_str in MONTH_NAMES:
            try:
                return date(int(m.group(3)), MONTH_NAMES[month_str], int(m.group(1)))
            except ValueError:
                pass

    # 4. Look for Month DD, YYYY (e.g., October 25, 2026)
    m = re.search(r'\b([A-Za-z]+)\s+(0?[1-9]|[12]\d|3[01]),?\s+(20\d\d)\b', text)
    if m:
        month_str = m.group(1).lower()
        if month_str in MONTH_NAMES:
            try:
                return date(int(m.group(3)), MONTH_NAMES[month_str], int(m.group(2)))
            except ValueError:
                pass

    # 5. Extract date embedded in string (e.g. 2021-06-30 23:59)
    m = re.search(r'(20\d\d-\d{2}-\d{2})', text)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass

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
