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

                CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url);
                CREATE INDEX IF NOT EXISTS idx_jobs_notified ON jobs(notified);
                CREATE INDEX IF NOT EXISTS idx_jobs_organization ON jobs(organization);
                CREATE INDEX IF NOT EXISTS idx_jobs_first_seen ON jobs(first_seen_at);
            """)
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        finally:
            conn.close()

    # ================================================================
    # Job Operations
    # ================================================================

    def job_exists(self, url: str) -> bool:
        """Check if a job URL has already been seen."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT 1 FROM jobs WHERE url = ?", (url,))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def insert_job(self, job_data: dict) -> Optional[int]:
        """
        Insert a new job into the database.
        Returns the job ID if inserted, None if already exists.
        """
        if self.job_exists(job_data.get("url", "")):
            logger.debug(f"Job already exists: {job_data.get('url')}")
            return None

        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO jobs (
                    title, organization, url, deadline, description,
                    raw_html, source, source_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_data.get("title", "Unknown"),
                job_data.get("organization", "Unknown"),
                job_data.get("url", ""),
                job_data.get("deadline"),
                job_data.get("description"),
                job_data.get("raw_html"),
                job_data.get("source"),
                job_data.get("source_type"),
            ))
            conn.commit()
            job_id = cursor.lastrowid
            logger.info(f"New job inserted [ID={job_id}]: {job_data.get('title')} @ {job_data.get('organization')}")
            return job_id
        except sqlite3.IntegrityError:
            logger.debug(f"Duplicate job URL: {job_data.get('url')}")
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
