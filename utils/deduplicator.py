"""
Job Deduplication & Fingerprinting Engine
==========================================
Identifies duplicate job postings across different sources,
handling title variations, organization name variations,
and cross-posting across portals and direct websites.
"""

import re
import hashlib
from typing import Optional


def normalize_org_name(org: Optional[str]) -> str:
    """Normalize bank/institution name for deduplication."""
    if not org:
        return ""
    org = str(org).lower()
    # Remove common corporate suffixes
    for suffix in [
        "limited", "plc", "ltd", "bank", "ব্যাংক", "finance",
        "financial", "institution", "corporation", "corp"
    ]:
        org = re.sub(r'\b' + re.escape(suffix) + r'\b', '', org)
    # Remove all non-alphanumeric chars
    org = re.sub(r'[^a-z0-9\u0980-\u09FF]+', '', org)
    return org.strip()


def normalize_title(title: Optional[str]) -> str:
    """Normalize job title for deduplication."""
    if not title:
        return ""
    t = str(title).lower()
    # Remove grade indicators: (grade-6), (10th grade), grade 9, etc.
    t = re.sub(r'\(?\b(?:grade|গ্রেড)[-:\s]*\d+\b\)?', '', t)
    t = re.sub(r'\b\d+(?:st|nd|rd|th)\s+grade\b', '', t)
    # Remove [View Circular] or [PDF Circular]
    t = re.sub(r'\[\s*(?:view|pdf)?\s*circular\s*\]', '', t)
    # Remove trailing/leading "of <Bank>", "for <Bank>"
    t = re.sub(r'\b(?:of|for)\s+[a-z\s]+bank[a-z\s]*$', '', t)
    # Remove non-alphanumeric except spaces
    t = re.sub(r'[^a-z0-9\u0980-\u09FF\s]+', ' ', t)
    # Collapse multiple spaces
    t = re.sub(r'\s{2,}', ' ', t)
    return t.strip()


def generate_job_fingerprint(title: str, org: str) -> str:
    """
    Generate a deterministic fingerprint hash from normalized title and organization.
    """
    norm_t = normalize_title(title)
    norm_o = normalize_org_name(org)

    # Sort tokens in title to be invariant to token order
    tokens = sorted(norm_t.split())
    sorted_title = " ".join(tokens)

    raw_key = f"{norm_o}::{sorted_title}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


def are_jobs_duplicate(title1: str, org1: str, title2: str, org2: str) -> bool:
    """
    Check if two job postings represent the exact same position.
    """
    fp1 = generate_job_fingerprint(title1, org1)
    fp2 = generate_job_fingerprint(title2, org2)
    if fp1 == fp2:
        return True

    # Check normalized orgs
    n_org1 = normalize_org_name(org1)
    n_org2 = normalize_org_name(org2)
    org_match = (
        (n_org1 and n_org2 and n_org1 == n_org2)
        or any(k in n_org1 for k in ["bb", "bscs"])
        or any(k in n_org2 for k in ["bb", "bscs"])
    )

    if not org_match:
        return False

    n_t1 = normalize_title(title1)
    n_t2 = normalize_title(title2)
    if not n_t1 or not n_t2:
        return False

    if n_t1 == n_t2:
        return True

    # Token overlap check
    tokens1 = set(n_t1.split())
    tokens2 = set(n_t2.split())

    # Critical distinction: If titles specify different disciplines or cadres, they are NOT duplicates!
    DISCIPLINES = {
        "civil", "mechanical", "electrical", "textile", "architecture",
        "leather", "computer", "it", "software", "law", "legal", "audit",
        "accounts", "cash", "general", "marketing", "agriculture", "medical",
        "system", "protocol", "financial", "analyst", "planning", "security"
    }
    d1 = tokens1 & DISCIPLINES
    d2 = tokens2 & DISCIPLINES
    if d1 != d2:
        return False

    if tokens1 and tokens2:
        overlap = len(tokens1 & tokens2) / max(len(tokens1), len(tokens2))
        if overlap >= 0.88:
            return True

    return False
