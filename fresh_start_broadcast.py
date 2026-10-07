import os
import sys
import io
import time
import requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from config.banks import BANKS
from storage.database import Database
from scrapers.bb_erecruitment_scraper import BBErecruitmentScraper
from scrapers.career_page_scraper import CareerPageScraper
from ai.job_analyzer import JobAnalyzer
from notifiers.telegram_bot import TelegramNotifier

print("=" * 60)
print("FRESH DATABASE RESET & ALL-BANKS INGESTION")
print("=" * 60)

# 1. Clear database
print("\n[Step 1] Wiping database for fresh start...")
for ext in ["", "-wal", "-shm"]:
    p = f"storage/jobs.db{ext}"
    if os.path.exists(p):
        try:
            os.remove(p)
            print(f"  Removed {p}")
        except Exception as e:
            print(f"  Could not remove {p}: {e}")

db = Database()
print("  Fresh database initialized.")

# 2. Scrape Bangladesh Bank BSCS e-Recruitment
print("\n[Step 2] Scraping Bangladesh Bank Central e-Recruitment (BSCS)...")
bb_scraper = BBErecruitmentScraper()
bb_jobs = bb_scraper.scrape_jobs()
print(f"  Found {len(bb_jobs)} active positions from BB BSCS.")

inserted_bb = 0
for j in bb_jobs:
    jid = db.insert_job(j)
    if jid:
        inserted_bb += 1
print(f"  Inserted {inserted_bb} fresh jobs from BB BSCS.")

# 3. Scrape ALL 104+ Banks & NBFIs
print("\n[Step 3] Scraping all 104+ banks & NBFIs in parallel...")
career_scraper = CareerPageScraper()
sources = [b for b in BANKS if b.get("short_name") != "BB_BSCS" and b.get("enabled", True)]
bank_jobs = career_scraper.scrape_all_concurrent(sources, max_workers=15)
print(f"  Discovered {len(bank_jobs)} raw candidates across individual bank career pages.")

inserted_banks = 0
for j in bank_jobs:
    jid = db.insert_job(j)
    if jid:
        inserted_banks += 1
print(f"  Inserted {inserted_banks} verified new jobs from individual bank career pages.")

# 3.5 Purge any expired jobs or duplicates
purged_expired = db.cleanup_expired_jobs()
purged_duplicates = db.cleanup_duplicates()
print(f"  Purged {purged_expired} expired jobs and {purged_duplicates} duplicate postings.")

total_jobs = db.get_job_count()
print(f"\n[Step 4] Total active, non-expired, non-duplicate circulars in database: {total_jobs}")

# 4. AI Analysis
print("\n[Step 5] Running AI analysis & bilingual summaries...")
analyzer = JobAnalyzer()
unanalyzed = db.get_unanalyzed_jobs()
print(f"  Analyzing {len(unanalyzed)} unanalyzed jobs...")
for j in unanalyzed:
    res = analyzer.analyze_job(j)
    if res:
        db.update_job_ai_analysis(j["id"], res)
print("  AI analysis complete!")

# 5. Broadcast to Telegram
print("\n[Step 6] Broadcasting all circulars to Telegram chat...")
telegram_notifier = TelegramNotifier()
all_active = db.get_all_jobs(limit=100, min_score=0.4)
print(f"  Broadcasting {len(all_active)} circulars to chat: {TELEGRAM_CHAT_ID}...")

# Header
welcome_header = (
    "🚀 <b>Fresh Bank Job Monitoring Initialized!</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"Database reset and repopulated with <b>{len(all_active)} active circulars</b> across 105+ banks & financial institutions.\n"
    "Delivering all current active circulars below:"
)
telegram_notifier.send_message(welcome_header)
time.sleep(1)

sent = 0
for j in all_active:
    card = telegram_notifier.format_job_message(j)
    if telegram_notifier.send_message(card):
        sent += 1
        db.mark_as_notified(j["id"])
    time.sleep(0.4)  # Rate limit protection

footer = (
    f"✅ <b>All {sent} Active Circulars Delivered!</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "• ⏱️ <b>Automated Monitoring:</b> Running every 30 minutes across ALL 105+ banks.\n"
    "• 🔄 <b>Chat Recovery:</b> Type <code>/fetchall</code> anytime if you ever delete your chat!\n"
    "• 📂 <b>Browse Categories:</b> Type <code>/categories</code> to filter by sector or discipline."
)
telegram_notifier.send_message(footer)

print(f"\nSuccessfully delivered {sent} circulars to Telegram!")
print("=" * 60)
