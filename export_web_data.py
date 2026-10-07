"""
Web Data Exporter for GitHub Pages
===================================
Exports database jobs and bank registry into static JSON files
consumed by the frontend web application.
"""

import json
import os
import sys
import io
import re
from datetime import date, datetime

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from config.banks import BANKS, ALL_SOURCES
from storage.database import Database
from utils.date_parser import parse_deadline, is_job_expired

def export_all():
    os.makedirs("data", exist_ok=True)
    db = Database()
    db.cleanup_expired_jobs()
    db.cleanup_duplicates()

    raw_jobs = db.get_all_jobs(limit=200, min_score=0.3)
    today = date.today()

    export_jobs = []
    for r in raw_jobs:
        dl_str = r.get("deadline")
        parsed_dl = parse_deadline(dl_str) or parse_deadline(r.get("title"))
        
        days_left = (parsed_dl - today).days if parsed_dl else None
        
        # Extract links from description or URL
        desc = r.get("description") or ""
        circ_match = re.search(r'Circular\s*PDF:\s*(https?://[^\s|]+)', desc)
        apply_match = re.search(r'Apply\s*Portal:\s*(https?://[^\s|]+)', desc)
        vacancies_match = re.search(r'Vacancies:\s*(\d+)', desc)
        salary_match = re.search(r'Salary:\s*([^|\n]+)', desc)
        req_match = re.search(r'Requirements:\s*([^|\n]+)', desc)

        circ_url = circ_match.group(1).strip() if circ_match else (r["url"] if r["url"].endswith(".pdf") or "erecruitment.bb.org.bd" in r["url"] else "")
        apply_url = apply_match.group(1).strip() if apply_match else ("https://erecruitment.bb.org.bd/onlineapp/joblist.php" if "erecruitment.bb.org.bd" in r["url"] else r["url"])

        # Determine category tag
        title_lower = (r.get("title") or "").lower()
        if any(k in title_lower for k in ["engineer", "architecture", "textile", "civil", "mechanical", "electrical"]):
            category = "engineering"
            category_label = "Engineering"
        elif any(k in title_lower for k in ["it", "system", "programmer", "software", "network"]):
            category = "it"
            category_label = "IT & Systems"
        elif any(k in title_lower for k in ["law", "legal"]):
            category = "law"
            category_label = "Law & Legal"
        elif any(k in title_lower for k in ["audit", "accounts", "accounting"]):
            category = "audit"
            category_label = "Audit & Accounts"
        elif any(k in title_lower for k in ["analyst", "financial"]):
            category = "analyst"
            category_label = "Financial Analyst"
        elif any(k in title_lower for k in ["officer", "manager", "trainee"]):
            category = "officer"
            category_label = "Officer & Management"
        else:
            category = "general"
            category_label = "General Banking"

        export_jobs.append({
            "id": r["id"],
            "title": r["title"],
            "organization": r["organization"],
            "url": r["url"],
            "deadline": str(parsed_dl) if parsed_dl else dl_str,
            "deadline_formatted": parsed_dl.strftime("%d %b %Y") if parsed_dl else dl_str,
            "days_left": days_left,
            "category": category,
            "category_label": category_label,
            "source": r.get("source"),
            "source_type": r.get("source_type"),
            "vacancies": vacancies_match.group(1) if vacancies_match else "Official Circular",
            "salary": salary_match.group(1).strip() if salary_match else "National Pay Scale",
            "eligibility": req_match.group(1).strip() if req_match else (r.get("ai_key_requirements") if isinstance(r.get("ai_key_requirements"), str) else ""),
            "ai_summary": r.get("ai_summary") or "",
            "ai_summary_bn": r.get("ai_summary_bn") or "",
            "ai_relevance_score": r.get("ai_relevance_score") or 0.85,
            "circular_url": circ_url,
            "apply_url": apply_url,
        })

    # Prepare bank directory including all scheduled banks, NBFIs and major portals
    export_banks = []
    for b in ALL_SOURCES:
        export_banks.append({
            "name": b["name"],
            "short_name": b.get("short_name", ""),
            "type": b.get("type", "bank"),
            "career_url": b.get("career_url", ""),
            "enabled": b.get("enabled", True),
        })

    # Metadata & Stats
    payload = {
        "generated_at": datetime.now().isoformat(),
        "today": today.isoformat(),
        "total_active_jobs": len(export_jobs),
        "total_monitored_institutions": len(ALL_SOURCES),
        "monitoring_frequency": "Every 30 Minutes",
        "bot_access_mode": db.get_access_mode(),
        "jobs": export_jobs,
        "banks": export_banks,
    }

    with open("data/jobs.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"✅ Successfully exported {len(export_jobs)} active circulars and {len(export_banks)} institutions to data/jobs.json")
    return payload

if __name__ == "__main__":
    export_all()
