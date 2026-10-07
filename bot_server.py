"""
Interactive Telegram Bot Server
================================
Listens for user commands in Telegram:
  /start   - Welcome & bot info
  /help    - List of available commands
  /latest  - Show the 5 most recent bank jobs
  /search  - Search jobs by keyword (e.g., /search IT, /search Officer)
  /stats   - Show database & monitoring statistics
  /check   - Run an instant on-demand scrape and report new jobs

Run locally:
  python bot_server.py
"""

import sys
import io
import html
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

# Force UTF-8 on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("bot_server")

from config.settings import TELEGRAM_BOT_TOKEN
from storage.database import Database
from main import scrape_all_sources, analyze_new_jobs, send_notifications

db = Database()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome = (
        "🏦 <b>Welcome to BD Bank Job Monitor!</b>\n\n"
        "I automatically monitor 25+ banks, financial institutions (NBFIs), "
        "and job portals across Bangladesh, using Gemini AI to filter and score relevant jobs.\n\n"
        "📋 <b>Available Commands:</b>\n"
        "• /latest — Show latest 5 bank job openings\n"
        "• /search &lt;keyword&gt; — Search jobs (e.g., <code>/search IT</code> or <code>/search Officer</code>)\n"
        "• /stats — View database statistics\n"
        "• /check — Trigger an instant scrape & alert\n"
        "• /help — Show this help message\n\n"
        "🤖 <i>New jobs are automatically announced here the moment they appear!</i>"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await start_command(update, context)


async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /latest command — show recent jobs."""
    recent_jobs = db.get_recent_jobs(limit=5)
    if not recent_jobs:
        await update.message.reply_text("📭 No jobs found in database yet.")
        return

    lines = ["🏦 <b>Latest Bank Job Postings:</b>\n"]
    for i, job in enumerate(recent_jobs, 1):
        title = html.escape(job.get("title", "Unknown"))
        org = html.escape(job.get("organization", "Unknown"))
        url = job.get("url", "")
        deadline = html.escape(job.get("deadline") or "Not specified")
        score = float(job.get("ai_relevance_score", 0) or 0)

        lines.append(
            f"<b>{i}. {title}</b>\n"
            f"   🏢 {org}\n"
            f"   📅 Deadline: {deadline}\n"
            f"   🎯 Match: {score:.0%}\n"
            f'   🔗 <a href="{html.escape(url)}">View / Apply</a>\n'
        )

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML, disable_web_page_preview=True)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search <keyword> command."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please specify a keyword to search.\nExample: <code>/search Officer</code> or <code>/search IT</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    keyword = " ".join(context.args).strip()
    # Query database for matching titles or organizations
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM jobs
            WHERE title LIKE ? OR organization LIKE ?
            ORDER BY id DESC LIMIT 5
            """,
            (f"%{keyword}%", f"%{keyword}%"),
        )
        matches = [dict(row) for row in cursor.fetchall()]

    if not matches:
        await update.message.reply_text(f"🔍 No jobs found matching '<b>{html.escape(keyword)}</b>'.", parse_mode=ParseMode.HTML)
        return

    lines = [f"🔍 <b>Search results for '{html.escape(keyword)}':</b>\n"]
    for i, job in enumerate(matches, 1):
        title = html.escape(job.get("title", "Unknown"))
        org = html.escape(job.get("organization", "Unknown"))
        url = job.get("url", "")
        lines.append(
            f"<b>{i}. {title}</b>\n"
            f"   🏢 {org}\n"
            f'   🔗 <a href="{html.escape(url)}">Apply</a>\n'
        )

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML, disable_web_page_preview=True)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command."""
    total_jobs = db.get_job_count()
    scrape_stats = db.get_scrape_stats()

    stats_msg = (
        "📊 <b>Bank Job Monitor — Statistics</b>\n\n"
        f"• <b>Total Jobs Tracked:</b> {total_jobs}\n"
        f"• <b>Total Scrape Runs:</b> {scrape_stats.get('total_scrapes', 0)}\n"
        f"• <b>Successful Scrapes:</b> {scrape_stats.get('successful', 0)}\n"
        f"• <b>Failed Scrapes:</b> {scrape_stats.get('failed', 0)}\n"
        f"• <b>New Jobs Discovered:</b> {scrape_stats.get('total_new_jobs', 0)}\n\n"
        "🤖 <i>Status: Active and monitoring</i>"
    )
    await update.message.reply_text(stats_msg, parse_mode=ParseMode.HTML)


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check command — run instant scrape."""
    status_msg = await update.message.reply_text("⏳ <i>Running instant scrape across all banks... This may take ~30s.</i>", parse_mode=ParseMode.HTML)

    try:
        new_jobs = scrape_all_sources(db)
        if new_jobs > 0:
            analyze_new_jobs(db)
            sent = send_notifications(db)
            await status_msg.edit_text(f"✅ Scrape complete! Found <b>{new_jobs}</b> new jobs and sent <b>{sent}</b> notifications.", parse_mode=ParseMode.HTML)
        else:
            await status_msg.edit_text("✅ Scrape complete! No new jobs posted since last check.", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error during on-demand check: {e}")
        await status_msg.edit_text(f"❌ Error during scrape: <code>{html.escape(str(e)[:200])}</code>", parse_mode=ParseMode.HTML)


def main():
    """Start interactive Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or "your_telegram" in TELEGRAM_BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN is not set in .env!")
        return

    print("🤖 Starting interactive Telegram bot server...")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("latest", latest_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("check", check_command))

    print("✅ Bot is online and listening for Telegram commands!")
    print("👉 Send /help or /latest in your Telegram group.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
