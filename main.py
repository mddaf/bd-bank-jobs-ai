"""
BD Bank Job Monitor — Main Orchestrator
==========================================
Entry point that coordinates the full pipeline:
  1. Scrape all enabled bank career pages & job portals
  2. Store new jobs in SQLite (with deduplication)
  3. Analyze new jobs using Gemini AI
  4. Send notifications via Telegram & Email

Usage:
  python main.py              # Run full pipeline once
  python main.py --scrape     # Only scrape (no AI/notifications)
  python main.py --notify     # Only send pending notifications
  python main.py --stats      # Show database statistics
"""

import sys
import time
import logging
import argparse
from datetime import datetime

# ================================================================
# Logging Setup (Windows-compatible: force UTF-8 on console)
# ================================================================
import io

# Force UTF-8 for console output on Windows
_console_handler = logging.StreamHandler(
    io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
)
_file_handler = logging.FileHandler("monitor.log", encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)-25s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[_console_handler, _file_handler],
)
logger = logging.getLogger("main")

# ================================================================
# Imports (after logging setup)
# ================================================================
from config.banks import get_enabled_sources, JOB_PORTALS
from storage.database import Database
from scrapers.career_page_scraper import CareerPageScraper
from scrapers.bdjobs_scraper import BdjobsScraper
from ai.job_analyzer import JobAnalyzer
from ai.gemini_client import GeminiClient
from notifiers.telegram_bot import TelegramNotifier
from notifiers.email_notifier import EmailNotifier


def scrape_all_sources(db: Database) -> int:
    """
    Scrape all enabled bank career pages and job portals.
    Returns the number of NEW jobs found.
    """
    logger.info("=" * 60)
    logger.info("PHASE 1: SCRAPING ALL SOURCES")
    logger.info("=" * 60)

    career_scraper = CareerPageScraper()
    bdjobs_scraper = BdjobsScraper()
    sources = get_enabled_sources()
    total_new = 0
    total_found = 0

    # ── Scrape direct career pages ──
    logger.info(f"\n📋 Scraping {len(sources)} bank career pages...")
    for source in sources:
        start_time = time.time()
        try:
            jobs = career_scraper.scrape(source)
            new_count = 0

            for job in jobs:
                job_id = db.insert_job(job)
                if job_id is not None:
                    new_count += 1

            duration = time.time() - start_time
            total_found += len(jobs)
            total_new += new_count

            db.log_scrape(
                source=source["short_name"],
                source_url=source["career_url"],
                status="success",
                jobs_found=len(jobs),
                new_jobs=new_count,
                duration_seconds=duration,
            )

            if new_count > 0:
                logger.info(f"  ✅ {source['name']}: {new_count} NEW jobs (of {len(jobs)} found)")
            else:
                logger.info(f"  ── {source['name']}: {len(jobs)} found, 0 new")

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"  ❌ {source['name']}: {e}")
            db.log_scrape(
                source=source.get("short_name", "UNKNOWN"),
                source_url=source.get("career_url", ""),
                status="error",
                error_message=str(e)[:500],
                duration_seconds=duration,
            )

    # ── Scrape bdjobs.com ──
    logger.info(f"\n📋 Scraping bdjobs.com...")
    start_time = time.time()
    try:
        bdjobs_jobs = bdjobs_scraper.scrape_all_categories()
        new_count = 0

        for job in bdjobs_jobs:
            job_id = db.insert_job(job)
            if job_id is not None:
                new_count += 1

        duration = time.time() - start_time
        total_found += len(bdjobs_jobs)
        total_new += new_count

        db.log_scrape(
            source="BDJOBS",
            source_url="https://jobs.bdjobs.com",
            status="success",
            jobs_found=len(bdjobs_jobs),
            new_jobs=new_count,
            duration_seconds=duration,
        )
        logger.info(f"  ✅ bdjobs.com: {new_count} NEW jobs (of {len(bdjobs_jobs)} found)")

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"  ❌ bdjobs.com: {e}")
        db.log_scrape(
            source="BDJOBS",
            source_url="https://jobs.bdjobs.com",
            status="error",
            error_message=str(e)[:500],
            duration_seconds=duration,
        )

    logger.info(f"\n📊 Scraping Summary: {total_found} total found, {total_new} NEW jobs saved")
    return total_new


def analyze_new_jobs(db: Database) -> int:
    """
    Analyze unanalyzed jobs using Gemini AI.
    Returns the number of jobs analyzed.
    """
    logger.info("=" * 60)
    logger.info("PHASE 2: AI ANALYSIS (Gemini)")
    logger.info("=" * 60)

    unanalyzed = db.get_unanalyzed_jobs()
    if not unanalyzed:
        logger.info("No new jobs to analyze.")
        return 0

    logger.info(f"📊 {len(unanalyzed)} jobs to analyze")

    try:
        analyzer = JobAnalyzer()
        results = analyzer.analyze_batch(unanalyzed)

        for job, analysis in results:
            if analysis:
                db.update_job_ai_analysis(job["id"], analysis)

        analyzed_count = sum(1 for _, a in results if a is not None)
        logger.info(f"✅ Analyzed {analyzed_count}/{len(unanalyzed)} jobs")
        return analyzed_count

    except ValueError as e:
        # Gemini API key not configured
        logger.warning(f"Gemini not available: {e}")
        logger.info("Skipping AI analysis. Jobs will be sent with basic info.")

        # Apply default analysis to all unanalyzed jobs
        for job in unanalyzed:
            default = {
                "summary_en": f"{job.get('title', 'Job')} at {job.get('organization', 'Unknown')}",
                "summary_bn": None,
                "relevance_score": 0.5,
                "category": "banking",
                "experience_level": "any",
                "key_requirements": [],
            }
            db.update_job_ai_analysis(job["id"], default)

        return len(unanalyzed)


def send_notifications(db: Database) -> int:
    """
    Send notifications for unnotified jobs.
    Returns the number of notifications sent.
    """
    logger.info("=" * 60)
    logger.info("PHASE 3: SENDING NOTIFICATIONS")
    logger.info("=" * 60)

    # Get jobs that scored above threshold and haven't been notified
    jobs = db.get_unnotified_jobs(min_relevance_score=0.3)

    if not jobs:
        logger.info("No pending notifications.")
        return 0

    logger.info(f"📬 {len(jobs)} jobs to notify about")
    sent_count = 0

    # ── Telegram ──
    telegram = TelegramNotifier()
    if telegram.is_configured:
        count = telegram.notify_batch(jobs)
        sent_count += count
        logger.info(f"  📱 Telegram: {count} notifications sent")
    else:
        logger.warning("  📱 Telegram not configured — skipping")

    # ── Email ──
    email = EmailNotifier()
    if email.is_configured:
        if email.send_daily_digest(jobs):
            sent_count += 1
            logger.info(f"  📧 Email digest sent to {email.receiver}")
    else:
        logger.warning("  📧 Email not configured — skipping")

    # Mark all as notified
    job_ids = [j["id"] for j in jobs]
    db.mark_many_as_notified(job_ids)
    logger.info(f"✅ Marked {len(job_ids)} jobs as notified")

    return sent_count


def show_stats(db: Database):
    """Display database statistics."""
    total_jobs = db.get_job_count()
    scrape_stats = db.get_scrape_stats()
    recent = db.get_recent_jobs(5)

    print("\n" + "=" * 60)
    print("  BD BANK JOB MONITOR — STATISTICS")
    print("=" * 60)
    print(f"\n  📊 Total Jobs in Database: {total_jobs}")
    print(f"  🔄 Total Scrape Runs: {scrape_stats.get('total_scrapes', 0)}")
    print(f"  ✅ Successful Scrapes: {scrape_stats.get('successful', 0)}")
    print(f"  ❌ Failed Scrapes: {scrape_stats.get('failed', 0)}")
    print(f"  🆕 Total New Jobs Found: {scrape_stats.get('total_new_jobs', 0)}")

    if recent:
        print(f"\n  📋 Most Recent Jobs:")
        print("  " + "─" * 56)
        for job in recent:
            score = job.get("ai_relevance_score", 0) or 0
            notified = "📬" if job.get("notified") else "⏳"
            print(f"  {notified} [{score:.0%}] {job.get('title', '?')[:40]}")
            print(f"       └── {job.get('organization', '?')}")

    print("\n" + "=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="BD Bank Job Monitor — AI-powered job notification agent"
    )
    parser.add_argument("--scrape", action="store_true", help="Only scrape (no AI/notifications)")
    parser.add_argument("--analyze", action="store_true", help="Only run AI analysis")
    parser.add_argument("--notify", action="store_true", help="Only send pending notifications")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--bot", action="store_true", help="Run interactive Telegram bot server (listens for /commands)")
    args = parser.parse_args()

    if args.bot:
        from bot_server import main as run_bot
        run_bot()
        return

    logger.info("🏦 BD Bank Job Monitor starting...")
    logger.info(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    db = Database()

    # If no specific flag, run the full pipeline
    run_all = not any([args.scrape, args.analyze, args.notify, args.stats, args.bot])

    try:
        if args.stats:
            show_stats(db)
            return

        if args.scrape or run_all:
            new_jobs = scrape_all_sources(db)

        if args.analyze or run_all:
            analyze_new_jobs(db)

        if args.notify or run_all:
            send_notifications(db)

        logger.info("\n✅ Pipeline complete!")
        show_stats(db)

    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user.")
    except Exception as e:
        logger.error(f"\n💥 Critical error: {e}", exc_info=True)

        # Try to send error alert
        try:
            telegram = TelegramNotifier()
            if telegram.is_configured:
                telegram.send_error_alert(str(e))
        except Exception:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()
