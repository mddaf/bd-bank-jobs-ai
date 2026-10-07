"""
Interactive Telegram Bot Server
================================
Features:
  /start   - Welcome & guide
  /help    - Complete list of commands
  /latest  - 5 most recent banking circulars
  /all     - Browse all jobs in database (paginated: /all [page])
  /jobs    - Alias for /all
  /search  - Search jobs by keyword (e.g., /search IT, /search Officer)
  /filter  - Filter by sector (e.g., /filter govt, /filter private, /filter islami, /filter nbfi)
  /banks   - View all 50+ monitored banks and institutions
  /resend  - Resend latest job alert cards to the chat
  /stats   - View database and monitoring statistics
  /check   - Run live scan with real-time multi-step progress indicator
"""

import sys
import io
import html
import asyncio
import logging
from telegram import Update, BotCommand
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

# Force UTF-8 encoding on Windows console
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("bot_server")

from config.settings import TELEGRAM_BOT_TOKEN
from config.banks import BANKS, ALL_SOURCES
from storage.database import Database
from scrapers.bb_erecruitment_scraper import BBErecruitmentScraper
from scrapers.career_page_scraper import CareerPageScraper
from scrapers.bdjobs_scraper import BdjobsScraper
from ai.job_analyzer import JobAnalyzer
from notifiers.telegram_bot import TelegramNotifier

db = Database()
telegram_notifier = TelegramNotifier()


async def send_msg(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, disable_preview: bool = True):
    """Safely send message directly to the chat without reply_to_message_id errors."""
    try:
        chat_id = update.effective_chat.id if update.effective_chat else update.message.chat_id
        return await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=disable_preview,
        )
    except Exception as e:
        logger.error(f"Failed to send bot response: {e}")
        return None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    welcome = (
        "🏦 <b>Bangladesh Bank & Financial Sector Job Monitor</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Autonomous monitoring of <b>105+ banks & financial institutions</b> across Bangladesh:\n"
        "• 🏛️ <b>Govt & Central Bank (9):</b> Bangladesh Bank (BSCS), Sonali, Janata, Agrani, Rupali, BASIC, BDBL, BKB, RAKUB, PKB\n"
        "• 🏢 <b>Private Commercial (33):</b> BRAC, City, EBL, MTB, Prime, Bank Asia, DBBL, IFIC, Jamuna, etc.\n"
        "• 🕌 <b>Islami Shariah (10):</b> IBBL, Al-Arafah, SIBL, SJIBL, EXIM, Union, Global Islami, etc.\n"
        "• 🌍 <b>Foreign & Digital (11):</b> Standard Chartered, HSBC, Woori, Nagad Digital, Kori Digital, etc.\n"
        "• 💼 <b>NBFIs (35):</b> IDLC, IPDC, LankaBangla, DBH, United Finance, IDCOL, etc.\n"
        "• 🌐 <b>Portals:</b> Bangladesh Bank e-Recruitment, Bdjobs, Skill Jobs\n\n"
        "📋 <b>Interactive Commands:</b>\n"
        "• /latest — 5 most recent job postings\n"
        "• /all [page] — Browse all jobs in database (e.g. <code>/all 1</code>, <code>/all 2</code>)\n"
        "• /search &lt;query&gt; — Search by title or bank (e.g. <code>/search Officer</code>, <code>/search IT</code>)\n"
        "• /filter &lt;type&gt; — Filter by sector (<code>govt</code>, <code>private</code>, <code>islami</code>, <code>nbfi</code>)\n"
        "• /banks — List all 105+ monitored institutions\n"
        "• /resend — Re-broadcast latest alerts into the chat\n"
        "• /check — Trigger an instant live scan with progress\n"
        "• /stats — View database & monitoring statistics\n"
        "• /help — Show this menu\n\n"
        "⚡ <i>New jobs are automatically verified by AI and broadcast here!</i>"
    )
    await send_msg(update, context, welcome)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await start_command(update, context)


async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /latest command — show 5 most recent jobs with clean card layout."""
    db.cleanup_expired_jobs()
    db.cleanup_duplicates()
    recent_jobs = db.get_recent_jobs(limit=5)
    if not recent_jobs:
        await send_msg(update, context, "📭 No active jobs found in database. Run <code>/check</code> to scan now!")
        return

    await send_msg(update, context, f"📢 <b>Showing {len(recent_jobs)} Most Recent Active Bank Job Circulars:</b>")

    for job in recent_jobs:
        card = telegram_notifier.format_job_message(job)
        await send_msg(update, context, card, disable_preview=False)
        await asyncio.sleep(0.3)


async def all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /all [page] — retrieve all verified jobs with pagination."""
    db.cleanup_expired_jobs()
    db.cleanup_duplicates()
    page = 1
    if context.args:
        try:
            page = max(1, int(context.args[0]))
        except ValueError:
            page = 1

    page_size = 5
    offset = (page - 1) * page_size
    total_jobs = db.get_job_count()
    jobs = db.get_all_jobs(limit=page_size, offset=offset, min_score=0.4)

    if not jobs:
        total_pages = max(1, (total_jobs + page_size - 1) // page_size)
        await send_msg(
            update,
            context,
            f"📭 No active jobs found on page {page}. (Total pages: {total_pages}).\nTry: <code>/all 1</code>",
        )
        return

    total_pages = max(1, (total_jobs + page_size - 1) // page_size)
    header = (
        f"📚 <b>Active Banking Jobs — Page {page} of {total_pages}</b>\n"
        f"<i>({total_jobs} active circulars verified & monitored)</i>\n"
        "───────────────────────\n"
    )
    await send_msg(update, context, header)

    for job in jobs:
        card = telegram_notifier.format_job_message(job)
        await send_msg(update, context, card, disable_preview=False)
        await asyncio.sleep(0.3)

    if page < total_pages:
        next_hint = f"👉 To view next page, type: <code>/all {page + 1}</code>"
        await send_msg(update, context, next_hint)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search <keyword> command."""
    db.cleanup_expired_jobs()
    db.cleanup_duplicates()
    if not context.args:
        await send_msg(
            update,
            context,
            "⚠️ Please provide a keyword to search.\n"
            "Examples:\n"
            "• <code>/search Officer</code>\n"
            "• <code>/search Engineer</code>\n"
            "• <code>/search Sonali</code>\n"
            "• <code>/search Analyst</code>",
        )
        return

    keyword = " ".join(context.args).strip()
    matches = db.search_jobs(keyword, limit=5)

    if not matches:
        await send_msg(
            update,
            context,
            f"🔍 No active bank jobs found matching '<b>{html.escape(keyword)}</b>'.\n"
            "Try broader keywords like <code>/search Bank</code> or <code>/search Officer</code>.",
        )
        return

    await send_msg(update, context, f"🔍 <b>Search results for '{html.escape(keyword)}' ({len(matches)} found):</b>")

    for job in matches:
        card = telegram_notifier.format_job_message(job)
        await send_msg(update, context, card, disable_preview=False)
        await asyncio.sleep(0.3)


async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /filter <type> (govt, private, islami, nbfi)."""
    db.cleanup_expired_jobs()
    db.cleanup_duplicates()
    if not context.args:
        await send_msg(
            update,
            context,
            "⚠️ Please specify a sector to filter:\n"
            "• <code>/filter govt</code> — State-owned & Bangladesh Bank circulars\n"
            "• <code>/filter private</code> — Private Commercial Banks\n"
            "• <code>/filter islami</code> — Shariah-based Islamic Banks\n"
            "• <code>/filter nbfi</code> — Non-Bank Financial Institutions",
        )
        return

    filter_type = context.args[0].lower().strip()
    type_map = {
        "govt": "state_owned",
        "government": "state_owned",
        "private": "private",
        "islami": "islami",
        "islamic": "islami",
        "nbfi": "nbfi",
    }
    target = type_map.get(filter_type, filter_type)
    jobs = db.get_jobs_by_type(target, limit=5)

    if not jobs:
        await send_msg(update, context, f"📭 No active jobs found for sector '<b>{html.escape(filter_type)}</b>'.")
        return

    await send_msg(update, context, f"🏷️ <b>Filter results for '{html.escape(filter_type.upper())}' ({len(jobs)} jobs):</b>")

    for job in jobs:
        card = telegram_notifier.format_job_message(job)
        await send_msg(update, context, card, disable_preview=False)
        await asyncio.sleep(0.3)


async def banks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /banks — list monitored banks and institutions."""
    text = (
        "🏦 <b>105+ Monitored Banks & Financial Institutions</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏛️ <b>Govt & Central Bank (SOCBs & SDBs):</b>\n"
        "• Bangladesh Bank (BSCS Central Recruitment)\n"
        "• Sonali Bank PLC, Janata Bank PLC, Agrani Bank PLC\n"
        "• Rupali Bank PLC, BASIC Bank PLC, BDBL\n"
        "• Bangladesh Krishi Bank (BKB), RAKUB, PKB, Ansar-VDP\n\n"
        "🏢 <b>Private Commercial Banks (33):</b>\n"
        "• BRAC Bank, Dutch-Bangla Bank (DBBL), Eastern Bank (EBL)\n"
        "• The City Bank, Mutual Trust Bank (MTB), Prime Bank\n"
        "• Bank Asia, AB Bank, Dhaka Bank, IFIC Bank, Jamuna Bank\n"
        "• Mercantile Bank, Midland Bank, Modhumoti Bank, Meghna Bank\n"
        "• National Bank, NCC Bank, NRB Bank, NRBC Bank, ONE Bank\n"
        "• Padma Bank, Premier Bank, Pubali Bank, SBAC Bank\n"
        "• Shimanto Bank, Southeast Bank, Trust Bank, UCB, Uttara Bank\n"
        "• Bengal Commercial, Citizens Bank, Bangladesh Commerce\n\n"
        "🕌 <b>Islamic Shariah Banks (10):</b>\n"
        "• Islami Bank Bangladesh (IBBL), Al-Arafah, SIBL, FSIBL\n"
        "• Shahjalal Islami (SJIBL), EXIM Bank, Union Bank\n"
        "• Global Islami Bank, ICB Islamic Bank, Standard Bank PLC\n\n"
        "🌍 <b>Foreign & Digital Banks (11):</b>\n"
        "• Standard Chartered, HSBC, Woori, Ceylon, SBI, HBL, Alfalah, Citi, NBP\n"
        "• Nagad Digital Bank, Kori Digital Bank\n\n"
        "💼 <b>NBFIs (35 Financial Institutions):</b>\n"
        "• IDLC, IPDC, LankaBangla, DBH, United Finance, IDCOL, BIFC, CVC\n"
        "• Fareast, FAS, First Finance, GSP, Hajj Finance, IIDFC, ILFSL\n"
        "• Meridian, MIDAS, National Finance, National Housing, Phoenix\n"
        "• Premier Leasing, Prime Finance, SABINCO, SFIL, UBICO, Uttara Finance...\n\n"
        "🌐 <b>Central Recruitment Portals:</b>\n"
        "• Bangladesh Bank e-Recruitment (BSCS)\n"
        "• bdjobs.com (Banking & NBFI categories)\n"
        "• Skill Jobs (Banking category)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>All monitored continuously by AI Agent!</i>"
    )
    await send_msg(update, context, text)


async def resend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /resend command — rebroadcast latest valid jobs into chat."""
    recent_jobs = db.get_recent_jobs(limit=10)
    if not recent_jobs:
        await send_msg(update, context, "📭 No jobs available in database to resend. Run <code>/check</code> first!")
        return

    await send_msg(update, context, f"🔄 <b>Re-broadcasting {len(recent_jobs)} latest job alerts to this chat...</b>")

    for job in recent_jobs:
        card = telegram_notifier.format_job_message(job)
        await send_msg(update, context, card, disable_preview=False)
        await asyncio.sleep(0.4)

    await send_msg(update, context, "✅ <b>All alerts successfully resent!</b>")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command."""
    total_jobs = db.get_job_count()
    scrape_stats = db.get_scrape_stats()

    stats_msg = (
        "📊 <b>BD Bank Job Monitor — Statistics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Total Active Circulars:</b> {total_jobs}\n"
        f"• <b>Monitored Institutions:</b> {len(BANKS)} Organizations\n"
        f"• <b>Total Scrape Runs:</b> {scrape_stats.get('total_scrapes', 0)}\n"
        f"• <b>Successful Scrapes:</b> {scrape_stats.get('successful', 0)}\n"
        f"• <b>Failed Scrapes:</b> {scrape_stats.get('failed', 0)}\n"
        f"• <b>New Jobs Discovered:</b> {scrape_stats.get('total_new_jobs', 0)}\n\n"
        "🤖 <i>Status: Fully Active & Monitoring</i>"
    )
    await send_msg(update, context, stats_msg)


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check command — on-demand scrape with live progress indication."""
    chat_id = update.effective_chat.id if update.effective_chat else update.message.chat_id
    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text="⏳ <b>[1/4]</b> 🏛️ <i>Connecting to Bangladesh Bank Central e-Recruitment (BSCS)...</i>",
        parse_mode=ParseMode.HTML,
    )

    try:
        # Step 1: Bangladesh Bank e-Recruitment
        bb_scraper = BBErecruitmentScraper()
        bb_jobs = await asyncio.to_thread(bb_scraper.scrape_jobs)
        new_bb = 0
        for j in bb_jobs:
            if db.insert_job(j) is not None:
                new_bb += 1

        # Step 2: Bank Career Pages & Portals
        await status_msg.edit_text(
            f"⏳ <b>[2/4]</b> 🏦 <i>BB e-Recruitment checked ({len(bb_jobs)} circulars). Now scanning 35+ private banks...</i>",
            parse_mode=ParseMode.HTML,
        )

        career_scraper = CareerPageScraper()
        sources = [s for s in BANKS if s.get("enabled", True) and s.get("short_name") != "BB_BSCS"]
        total_career_new = 0

        def scan_career_pages():
            cnt = 0
            for s in sources:
                try:
                    c_jobs = career_scraper.scrape(s)
                    for j in c_jobs:
                        if db.insert_job(j) is not None:
                            cnt += 1
                except Exception:
                    pass
            return cnt

        total_career_new = await asyncio.to_thread(scan_career_pages)

        # Step 3: AI Analysis
        total_new = new_bb + total_career_new
        await status_msg.edit_text(
            f"⏳ <b>[3/4]</b> 🧠 <i>Scraping complete ({total_new} new jobs found). Running Gemini AI analysis...</i>",
            parse_mode=ParseMode.HTML,
        )

        unanalyzed = db.get_unanalyzed_jobs()
        analyzed_count = 0
        if unanalyzed:
            analyzer = JobAnalyzer()
            results = await asyncio.to_thread(analyzer.analyze_batch, unanalyzed)
            for j, analysis in results:
                if analysis:
                    db.update_job_ai_analysis(j["id"], analysis)
            analyzed_count = len(results)

        # Step 4: Notifications
        await status_msg.edit_text(
            f"⏳ <b>[4/4]</b> 📬 <i>AI analysis complete ({analyzed_count} analyzed). Delivering notifications...</i>",
            parse_mode=ParseMode.HTML,
        )

        unnotified = db.get_unnotified_jobs(min_relevance_score=0.4)
        sent_count = 0
        for j in unnotified:
            card = telegram_notifier.format_job_message(j)
            await send_msg(update, context, card, disable_preview=False)
            db.mark_as_notified(j["id"])
            sent_count += 1
            await asyncio.sleep(0.4)

        summary_text = (
            f"✅ <b>Live Scan Complete!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• 🏛️ <b>Govt Bank Circulars (BB BSCS):</b> {len(bb_jobs)} active\n"
            f"• 🆕 <b>New Jobs Discovered:</b> {total_new}\n"
            f"• 🧠 <b>Jobs Analyzed by AI:</b> {analyzed_count}\n"
            f"• 📢 <b>Notifications Delivered:</b> {sent_count}\n\n"
            f"👉 Type <code>/latest</code> or <code>/all</code> to browse anytime!"
        )
        await status_msg.edit_text(summary_text, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error during on-demand check: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Error during scan:</b> <code>{html.escape(str(e)[:250])}</code>",
            parse_mode=ParseMode.HTML,
        )


async def setup_bot_commands(application: Application):
    """Register menu commands with Telegram API."""
    commands = [
        BotCommand("latest", "Show 5 most recent bank jobs"),
        BotCommand("all", "Browse all jobs in database (/all [page])"),
        BotCommand("search", "Search jobs by keyword (/search IT)"),
        BotCommand("filter", "Filter by sector (/filter govt/private/islami/nbfi)"),
        BotCommand("banks", "List all 50+ monitored banks & NBFIs"),
        BotCommand("resend", "Re-broadcast latest job alerts to chat"),
        BotCommand("check", "Run instant scrape with progress indicator"),
        BotCommand("stats", "View database & monitoring statistics"),
        BotCommand("help", "Show help and command guide"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        logger.info("Registered bot commands menu with Telegram.")
    except Exception as e:
        logger.warning(f"Failed to set bot commands: {e}")


def main():
    """Start interactive Telegram bot server."""
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if not TELEGRAM_BOT_TOKEN or "your_telegram" in TELEGRAM_BOT_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN is not set in .env!")
        return

    print("🤖 Starting BD Bank Job Monitor Bot Server...")
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .concurrent_updates(True)
        .post_init(setup_bot_commands)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("latest", latest_command))
    app.add_handler(CommandHandler("all", all_command))
    app.add_handler(CommandHandler("jobs", all_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("filter", filter_command))
    app.add_handler(CommandHandler("banks", banks_command))
    app.add_handler(CommandHandler("resend", resend_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("check", check_command))

    print("✅ Bot is online with live progress indicators & all new commands!")
    app.run_polling(poll_interval=0.5, timeout=10, drop_pending_updates=True)


if __name__ == "__main__":
    main()
