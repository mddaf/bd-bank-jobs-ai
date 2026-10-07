"""
Database Layer — SQLite Operations
====================================
Handles all persistent storage for jobs, scrape logs, and deduplication.
Uses SQLite for zero-config, file-based storage.
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict
from config.settings import DB_PATH

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager for the job monitor."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
        return conn

    def _init_db(self):
        """Initialize database tables if they don't exist."""
        conn = self._get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    organization TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    deadline TEXT,
                    description TEXT,
                    raw_html TEXT,
                    source TEXT,
                    source_type TEXT,
                    fingerprint TEXT,
                    ai_summary TEXT,
                    ai_summary_bn TEXT,
                    ai_relevance_score REAL DEFAULT 0.0,
                    ai_category TEXT,
                    ai_experience_level TEXT,
                    ai_key_requirements TEXT,
                    notified INTEGER DEFAULT 0,
                    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS scrape_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    source_url TEXT,
                    status TEXT NOT NULL,
                    jobs_found INTEGER DEFAULT 0,
                    new_jobs INTEGER DEFAULT 0,
                    error_message TEXT,
                    duration_seconds REAL,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS expired_jobs (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    organization TEXT,
                    deadline TEXT,
                    expired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS authorized_users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    access_type TEXT DEFAULT 'bot',
                    approved_by TEXT,
                    status TEXT DEFAULT 'approved',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);
                CREATE INDEX IF NOT EXISTS idx_jobs_notified ON jobs(notified);
                CREATE INDEX IF NOT EXISTS idx_jobs_organization ON jobs(organization);
                CREATE INDEX IF NOT EXISTS idx_jobs_first_seen ON jobs(first_seen_at);
                CREATE INDEX IF NOT EXISTS idx_expired_jobs_url ON expired_jobs(url);
                CREATE INDEX IF NOT EXISTS idx_authorized_users_status ON authorized_users(status);
            """)

            # Add fingerprint column and index to existing DB if missing
            try:
                conn.execute("ALTER TABLE jobs ADD COLUMN fingerprint TEXT")
            except sqlite3.OperationalError:
                pass  # Already exists

            try:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs(fingerprint)")
            except sqlite3.OperationalError:
                pass

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        finally:
            conn.close()

        # Run automated cleanup on startup
        self.cleanup_expired_jobs()
        self.cleanup_duplicates()

    # ================================================================
    # Job Operations
    # ================================================================

    def is_job_blacklisted(self, url: str) -> bool:
        """Check if a job URL has expired and was blacklisted."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT 1 FROM expired_jobs WHERE url = ?", (url,))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def blacklist_expired_job(self, url: str, title: str = "", organization: str = "", deadline: str = ""):
        """Permanently record an expired job so it can NEVER be re-added."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR IGNORE INTO expired_jobs (url, title, organization, deadline)
                VALUES (?, ?, ?, ?)
            """, (url, title, organization, deadline))
            conn.commit()
        finally:
            conn.close()

    def job_exists(self, url: str) -> bool:
        """Check if a job URL already exists in active jobs OR expired blacklist."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT 1 FROM jobs WHERE url = ?
                UNION
                SELECT 1 FROM expired_jobs WHERE url = ?
            """, (url, url))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def cleanup_expired_jobs(self) -> int:
        """
        Smart automated deletion:
        Finds all active jobs whose application deadline has passed,
        permanently blacklists them in expired_jobs, and deletes them from active jobs.
        Returns the number of expired jobs removed.
        """
        from utils.date_parser import is_job_expired, parse_deadline
        conn = self._get_connection()
        removed_count = 0
        try:
            cursor = conn.execute("SELECT id, title, organization, url, deadline, description FROM jobs")
            rows = cursor.fetchall()
            for r in rows:
                job_dict = dict(r)
                if is_job_expired(job_dict):
                    dl = r["deadline"] or str(parse_deadline(r["title"])) or "Expired"
                    conn.execute("""
                        INSERT OR IGNORE INTO expired_jobs (url, title, organization, deadline)
                        VALUES (?, ?, ?, ?)
                    """, (r["url"], r["title"], r["organization"], str(dl)))
                    conn.execute("DELETE FROM jobs WHERE id = ?", (r["id"],))
                    removed_count += 1
                    logger.info(f"Smart-deleted expired job [ID={r['id']}]: {r['title']} (Deadline: {dl})")

            if removed_count > 0:
                conn.commit()
                logger.info(f"Automated cleanup: removed and blacklisted {removed_count} expired jobs.")
            return removed_count
        finally:
            conn.close()

    def cleanup_duplicates(self) -> int:
        """
        Smart automated duplicate removal:
        Scans all active jobs, detects duplicates based on normalized title and organization,
        keeps the best version (highest score or PDF link), and removes duplicates.
        Returns the number of duplicate jobs purged.
        """
        from utils.deduplicator import are_jobs_duplicate, generate_job_fingerprint
        conn = self._get_connection()
        removed_count = 0
        try:
            cursor = conn.execute("SELECT id, title, organization, url, fingerprint, ai_relevance_score FROM jobs ORDER BY id ASC")
            all_jobs = [dict(r) for r in cursor.fetchall()]

            seen_fps = {}
            to_delete_ids = set()

            for j in all_jobs:
                jid = j["id"]
                fp = j.get("fingerprint") or generate_job_fingerprint(j["title"], j["organization"])

                # Update fingerprint in DB if missing
                if not j.get("fingerprint"):
                    conn.execute("UPDATE jobs SET fingerprint = ? WHERE id = ?", (fp, jid))

                if fp in seen_fps:
                    existing = seen_fps[fp]
                    # Keep the one with .pdf link or higher score
                    if j["url"].endswith(".pdf") and not existing["url"].endswith(".pdf"):
                        to_delete_ids.add(existing["id"])
                        seen_fps[fp] = j
                    else:
                        to_delete_ids.add(jid)
                else:
                    # Also check fuzzy duplicate with other registered jobs
                    is_dup = False
                    for prev_fp, prev_job in seen_fps.items():
                        if are_jobs_duplicate(j["title"], j["organization"], prev_job["title"], prev_job["organization"]):
                            if j["url"].endswith(".pdf") and not prev_job["url"].endswith(".pdf"):
                                to_delete_ids.add(prev_job["id"])
                                seen_fps[prev_fp] = j
                            else:
                                to_delete_ids.add(jid)
                            is_dup = True
                            break
                    if not is_dup:
                        seen_fps[fp] = j

            for del_id in to_delete_ids:
                conn.execute("DELETE FROM jobs WHERE id = ?", (del_id,))
                removed_count += 1

            if removed_count > 0:
                conn.commit()
                logger.info(f"Automated deduplication: removed {removed_count} duplicate postings from database.")
            return removed_count
        finally:
            conn.close()

    def insert_job(self, job_data: dict) -> Optional[int]:
        """
        Insert a new job into the database.
        Automated validation:
          - Rejects if URL is already active or in expired blacklist.
          - Rejects if deadline has already passed, automatically blacklisting it.
          - Rejects duplicate postings across banks/portals using deterministic fingerprint.
        Returns job ID if inserted, None otherwise.
        """
        from utils.deduplicator import generate_job_fingerprint, are_jobs_duplicate
        from utils.date_parser import is_job_expired, parse_deadline

        url = (job_data.get("url") or "").strip()
        title = job_data.get("title", "Unknown")
        org = job_data.get("organization", "Unknown")
        deadline = job_data.get("deadline")

        if not url:
            return None

        # 1. Check if URL already known or blacklisted
        if self.job_exists(url):
            logger.debug(f"Job already exists or is blacklisted: {url}")
            return None

        # 2. Automated deadline check: if already passed, never add it!
        parsed_dl = parse_deadline(deadline) or parse_deadline(title)
        if is_job_expired(job_data):
            self.blacklist_expired_job(url=url, title=title, organization=org, deadline=str(parsed_dl) if parsed_dl else "Expired")
            logger.info(f"Automated rejection: deadline expired for '{title}'. Blacklisted.")
            return None

        # 3. Automated duplicate check (Cross-source & fuzzy matching)
        fp = generate_job_fingerprint(title, org)
        conn = self._get_connection()
        try:
            # Check exact fingerprint match
            cursor = conn.execute("SELECT id, title, organization, url FROM jobs WHERE fingerprint = ?", (fp,))
            match = cursor.fetchone()
            if match:
                logger.info(f"Auto-filtered duplicate: '{title}' @ '{org}' already exists [ID={match['id']}]")
                # If new source has official PDF link while stored one doesn't, upgrade stored URL
                if url.endswith(".pdf") and not match["url"].endswith(".pdf"):
                    conn.execute("UPDATE jobs SET url = ? WHERE id = ?", (url, match["id"]))
                    conn.commit()
                    logger.info(f"Upgraded job [ID={match['id']}] URL to official circular: {url}")
                return None

            # Check fuzzy cross-posting duplicate from same bank
            cursor = conn.execute("SELECT id, title, organization, url FROM jobs ORDER BY id DESC LIMIT 40")
            recent = [dict(r) for r in cursor.fetchall()]
            for r in recent:
                if are_jobs_duplicate(title, org, r["title"], r["organization"]):
                    logger.info(f"Auto-filtered duplicate: '{title}' matches existing job [ID={r['id']}]: '{r['title']}'")
                    if url.endswith(".pdf") and not r["url"].endswith(".pdf"):
                        conn.execute("UPDATE jobs SET url = ? WHERE id = ?", (url, r["id"]))
                        conn.commit()
                        logger.info(f"Upgraded job [ID={r['id']}] URL to official circular: {url}")
                    return None

            # Insert new unique job
            cursor = conn.execute("""
                INSERT INTO jobs (
                    title, organization, url, deadline, description,
                    raw_html, source, source_type, fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title,
                org,
                url,
                str(parsed_dl) if parsed_dl else deadline,
                job_data.get("description"),
                job_data.get("raw_html"),
                job_data.get("source"),
                job_data.get("source_type"),
                fp,
            ))
            conn.commit()
            job_id = cursor.lastrowid
            logger.info(f"New job inserted [ID={job_id}]: {title} @ {org}")
            return job_id
        except sqlite3.IntegrityError:
            logger.debug(f"Duplicate job URL: {url}")
            return None
        finally:
            conn.close()

    def update_job_ai_analysis(self, job_id: int, analysis: dict):
        """Update a job record with AI analysis results."""
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE jobs SET
                    ai_summary = ?,
                    ai_summary_bn = ?,
                    ai_relevance_score = ?,
                    ai_category = ?,
                    ai_experience_level = ?,
                    ai_key_requirements = ?
                WHERE id = ?
            """, (
                analysis.get("summary_en"),
                analysis.get("summary_bn"),
                analysis.get("relevance_score", 0.0),
                analysis.get("category"),
                analysis.get("experience_level"),
                str(analysis.get("key_requirements", [])),
                job_id,
            ))
            conn.commit()
            logger.info(f"AI analysis updated for job ID={job_id}")
        finally:
            conn.close()

    def get_unnotified_jobs(self, min_relevance_score: float = 0.0) -> list:
        """Get all jobs that haven't been notified yet."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM jobs
                WHERE notified = 0 AND ai_relevance_score >= ?
                ORDER BY ai_relevance_score DESC, first_seen_at DESC
            """, (min_relevance_score,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_unanalyzed_jobs(self) -> list:
        """Get jobs that haven't been analyzed by AI yet."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM jobs
                WHERE ai_summary IS NULL
                ORDER BY first_seen_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def mark_as_notified(self, job_id: int):
        """Mark a job as having been notified."""
        conn = self._get_connection()
        try:
            conn.execute("UPDATE jobs SET notified = 1 WHERE id = ?", (job_id,))
            conn.commit()
        finally:
            conn.close()

    def mark_many_as_notified(self, job_ids: list):
        """Mark multiple jobs as notified."""
        conn = self._get_connection()
        try:
            conn.executemany(
                "UPDATE jobs SET notified = 1 WHERE id = ?",
                [(jid,) for jid in job_ids]
            )
            conn.commit()
        finally:
            conn.close()

    def get_recent_jobs(self, limit: int = 20) -> list:
        """Get the most recent jobs."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM jobs
                ORDER BY first_seen_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_job_count(self) -> int:
        """Get total number of jobs in the database."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM jobs")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def get_all_jobs(self, limit: int = 20, offset: int = 0, min_score: float = 0.4) -> list:
        """Retrieve all verified jobs with pagination."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM jobs
                WHERE ai_relevance_score >= ?
                ORDER BY first_seen_at DESC, id DESC
                LIMIT ? OFFSET ?
            """, (min_score, limit, offset))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def search_jobs(self, keyword: str, limit: int = 15) -> list:
        """Search jobs by title or organization."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM jobs
                WHERE (title LIKE ? OR organization LIKE ? OR description LIKE ?)
                  AND (ai_relevance_score >= 0.4 OR ai_relevance_score IS NULL)
                ORDER BY first_seen_at DESC, id DESC
                LIMIT ?
            """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_jobs_by_type(self, source_type: str, limit: int = 15) -> list:
        """Filter jobs by institution type (e.g., state_owned, private, islami, nbfi)."""
        return self.get_jobs_by_category_tag(source_type, limit=limit)

    def get_jobs_by_category_tag(self, tag: str, limit: int = 10, offset: int = 0) -> list:
        """
        Filter jobs by predefined categories or disciplines:
          - govt: State-owned / Bangladesh Bank BSCS
          - private: Private Commercial Banks
          - islami: Islamic Banks
          - nbfi: Non-Bank Financial Institutions
          - engineering: Civil, Mechanical, Electrical, Textile, Architecture, etc.
          - it: IT, Systems, Computer, Software
          - law: Law & Legal Officers
          - audit: Audit & Accounts
          - analyst: Financial Analyst, Research
          - officer: General Officers, Management Trainees
        """
        conn = self._get_connection()
        try:
            tag = tag.lower().strip()
            params = []

            if tag in ["govt", "government", "state_owned"]:
                where_clause = "(source_type = 'state_owned' OR source = 'BB_BSCS' OR organization LIKE '%Bangladesh Bank%' OR organization LIKE '%Sonali%' OR organization LIKE '%Janata%' OR organization LIKE '%Agrani%' OR organization LIKE '%Rupali%' OR organization LIKE '%BASIC%' OR organization LIKE '%Krishi%' OR organization LIKE '%Karmasangsthan%' OR organization LIKE '%Probashi%' OR organization LIKE '%Ansar%')"
            elif tag in ["private", "commercial"]:
                where_clause = "(source_type = 'private' OR (source_type != 'state_owned' AND source != 'BB_BSCS' AND source_type != 'islami' AND source_type != 'nbfi'))"
            elif tag in ["islami", "islamic"]:
                where_clause = "(source_type = 'islami' OR title LIKE '%islami%' OR organization LIKE '%islami%' OR organization LIKE '%al-arafah%' OR organization LIKE '%sibl%')"
            elif tag in ["nbfi", "leasing", "finance"]:
                where_clause = "(source_type = 'nbfi' OR organization LIKE '%finance%' OR organization LIKE '%leasing%' OR organization LIKE '%idlc%' OR organization LIKE '%ipdc%')"
            elif tag in ["engineering", "engineer", "tech"]:
                where_clause = "(title LIKE '%engineer%' OR title LIKE '%civil%' OR title LIKE '%mechanical%' OR title LIKE '%electrical%' OR title LIKE '%textile%' OR title LIKE '%architecture%' OR title LIKE '%leather%')"
            elif tag in ["it", "tech_it", "software", "system"]:
                where_clause = "(title LIKE '%system%' OR title LIKE '%it%' OR title LIKE '%computer%' OR title LIKE '%software%' OR title LIKE '%developer%' OR title LIKE '%programmer%')"
            elif tag in ["law", "legal"]:
                where_clause = "(title LIKE '%law%' OR title LIKE '%legal%')"
            elif tag in ["audit", "accounts", "accounting"]:
                where_clause = "(title LIKE '%audit%' OR title LIKE '%account%')"
            elif tag in ["analyst", "financial_analyst"]:
                where_clause = "(title LIKE '%analyst%')"
            elif tag in ["officer", "general"]:
                where_clause = "(title LIKE '%officer%' OR title LIKE '%manager%' OR title LIKE '%executive%')"
            else:
                where_clause = "(title LIKE ? OR organization LIKE ? OR description LIKE ?)"
                params.extend([f"%{tag}%", f"%{tag}%", f"%{tag}%"])

            sql = f"""
                SELECT * FROM jobs
                WHERE {where_clause}
                ORDER BY first_seen_at DESC, id DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            cursor = conn.execute(sql, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_category_counts(self) -> dict:
        """Get live job count for each main category and discipline."""
        conn = self._get_connection()
        try:
            counts = {}
            queries = {
                "govt": "source_type = 'state_owned' OR source = 'BB_BSCS' OR organization LIKE '%Bank%'",
                "private": "source_type = 'private'",
                "islami": "source_type = 'islami'",
                "nbfi": "source_type = 'nbfi' OR organization LIKE '%Finance%'",
                "engineering": "title LIKE '%engineer%' OR title LIKE '%civil%' OR title LIKE '%mechanical%' OR title LIKE '%electrical%' OR title LIKE '%textile%' OR title LIKE '%architecture%'",
                "it": "title LIKE '%system%' OR title LIKE '%computer%' OR title LIKE '%software%'",
                "law": "title LIKE '%law%' OR title LIKE '%legal%'",
                "audit": "title LIKE '%audit%' OR title LIKE '%account%'",
                "analyst": "title LIKE '%analyst%'",
                "officer": "title LIKE '%officer%'",
            }
            for key, condition in queries.items():
                cur = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {condition}")
                counts[key] = cur.fetchone()[0]
            cur = conn.execute("SELECT COUNT(*) FROM jobs")
            counts["total"] = cur.fetchone()[0]
            return counts
        finally:
            conn.close()

    def reset_all_notified(self) -> int:
        """Reset notified flag so jobs can be rebroadcast/resent."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("UPDATE jobs SET notified = 0 WHERE ai_relevance_score >= 0.5")
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    # ================================================================
    # Scrape Log Operations
    # ================================================================

    def log_scrape(self, source: str, source_url: str, status: str,
                   jobs_found: int = 0, new_jobs: int = 0,
                   error_message: str = None, duration_seconds: float = None):
        """Log a scraping attempt."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO scrape_logs (
                    source, source_url, status, jobs_found,
                    new_jobs, error_message, duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (source, source_url, status, jobs_found,
                  new_jobs, error_message, duration_seconds))
            conn.commit()
        finally:
            conn.close()

    def get_scrape_stats(self) -> dict:
        """Get overall scraping statistics."""
        conn = self._get_connection()
        try:
            stats = {}
            cursor = conn.execute("""
                SELECT
                    COUNT(*) as total_scrapes,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as failed,
                    SUM(new_jobs) as total_new_jobs
                FROM scrape_logs
            """)
            row = cursor.fetchone()
            if row:
                stats = dict(row)
            return stats
        finally:
            conn.close()

    # ================================================================
    # Settings & Access Control Operations
    # ================================================================

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value by key."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default
        finally:
            conn.close()

    def set_setting(self, key: str, value: str):
        """Set a setting key-value pair."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
            """, (key, str(value)))
            conn.commit()
        finally:
            conn.close()

    def get_access_mode(self) -> str:
        """Get current access mode ('public' or 'private'). Defaults to 'private'."""
        mode = self.get_setting("access_mode")
        if not mode:
            mode = os.getenv("BOT_ACCESS_MODE", "private").lower()
            self.set_setting("access_mode", mode)
        return mode

    def set_access_mode(self, mode: str) -> str:
        """Toggle access mode to 'public' or 'private'."""
        normalized = "public" if mode.lower() == "public" else "private"
        self.set_setting("access_mode", normalized)
        return normalized

    def is_user_authorized(self, user_id: str) -> bool:
        """Check if user_id is explicitly approved in authorized_users."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT status FROM authorized_users WHERE user_id = ? AND status = 'approved'",
                (str(user_id),)
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def authorize_user(self, user_id: str, username: Optional[str] = None,
                       full_name: Optional[str] = None, access_type: str = "bot",
                       approved_by: Optional[str] = None) -> bool:
        """Grant authorization to a user."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO authorized_users (
                    user_id, username, full_name, access_type, approved_by, status, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'approved', CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = coalesce(excluded.username, authorized_users.username),
                    full_name = coalesce(excluded.full_name, authorized_users.full_name),
                    access_type = excluded.access_type,
                    approved_by = excluded.approved_by,
                    status = 'approved',
                    updated_at = CURRENT_TIMESTAMP
            """, (str(user_id), username, full_name, access_type, approved_by))
            conn.commit()
            return True
        finally:
            conn.close()

    def record_access_request(self, user_id: str, username: Optional[str] = None,
                              full_name: Optional[str] = None, request_type: str = "bot") -> bool:
        """Record or update a pending join or bot usage access request."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT INTO authorized_users (
                    user_id, username, full_name, access_type, status, updated_at
                ) VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = coalesce(excluded.username, authorized_users.username),
                    full_name = coalesce(excluded.full_name, authorized_users.full_name),
                    access_type = excluded.access_type,
                    status = 'pending',
                    updated_at = CURRENT_TIMESTAMP
            """, (str(user_id), username, full_name, request_type))
            conn.commit()
            return True
        finally:
            conn.close()

    def reject_user(self, user_id: str, rejected_by: Optional[str] = None) -> bool:
        """Mark access request as rejected."""
        conn = self._get_connection()
        try:
            conn.execute("""
                UPDATE authorized_users
                SET status = 'rejected', approved_by = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (rejected_by, str(user_id)))
            conn.commit()
            return True
        finally:
            conn.close()

    def revoke_user(self, user_id: str) -> bool:
        """Remove user authorization."""
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM authorized_users WHERE user_id = ?", (str(user_id),))
            conn.commit()
            return True
        finally:
            conn.close()

    def list_authorized_users(self, status: str = "approved") -> List[Dict]:
        """List users by status (approved, pending, rejected)."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM authorized_users WHERE status = ? ORDER BY updated_at DESC",
                (status,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
