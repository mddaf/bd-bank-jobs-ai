"""
Database Layer — SQLite Operations
====================================
Handles all persistent storage for jobs, scrape logs, and deduplication.
Uses SQLite for zero-config, file-based storage.
"""

import sqlite3
import logging
from datetime import datetime
from typing import Optional
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

                CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);
                CREATE INDEX IF NOT EXISTS idx_jobs_notified ON jobs(notified);
                CREATE INDEX IF NOT EXISTS idx_jobs_organization ON jobs(organization);
                CREATE INDEX IF NOT EXISTS idx_jobs_first_seen ON jobs(first_seen_at);
                CREATE INDEX IF NOT EXISTS idx_expired_jobs_url ON expired_jobs(url);
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
        from utils.date_parser import is_deadline_passed, parse_deadline
        conn = self._get_connection()
        removed_count = 0
        try:
            cursor = conn.execute("SELECT id, title, organization, url, deadline FROM jobs")
            rows = cursor.fetchall()
            for r in rows:
                deadline = r["deadline"]
                parsed_dl = parse_deadline(deadline) or parse_deadline(r["title"])
                if parsed_dl and is_deadline_passed(str(parsed_dl)):
                    conn.execute("""
                        INSERT OR IGNORE INTO expired_jobs (url, title, organization, deadline)
                        VALUES (?, ?, ?, ?)
                    """, (r["url"], r["title"], r["organization"], str(parsed_dl)))
                    conn.execute("DELETE FROM jobs WHERE id = ?", (r["id"],))
                    removed_count += 1
                    logger.info(f"Smart-deleted expired job [ID={r['id']}]: {r['title']} (Deadline: {parsed_dl})")

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
        from utils.date_parser import is_deadline_passed, parse_deadline

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
        if parsed_dl and is_deadline_passed(str(parsed_dl)):
            self.blacklist_expired_job(url=url, title=title, organization=org, deadline=str(parsed_dl))
            logger.info(f"Automated rejection: deadline expired for '{title}' (Deadline: {parsed_dl}). Blacklisted.")
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
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM jobs
                WHERE (source_type LIKE ? OR ai_category LIKE ?)
                  AND (ai_relevance_score >= 0.4 OR ai_relevance_score IS NULL)
                ORDER BY first_seen_at DESC, id DESC
                LIMIT ?
            """, (f"%{source_type}%", f"%{source_type}%", limit))
            return [dict(row) for row in cursor.fetchall()]
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
