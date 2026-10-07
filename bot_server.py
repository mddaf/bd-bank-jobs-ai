"""
Interactive Telegram Bot Server
================================
Features:
  /start       - Welcome & interactive quick menu
  /categories  - One-tap category browser with live counts (Govt, IT, Engineering, Law, etc.)
  /search      - Instant search or quick-search chips
  /filter      - Filter by sector or discipline
  /latest      - 5 most recent banking circulars
  /all         - Browse all jobs in database with interactive pagination buttons
  /banks       - View all 105+ monitored banks and institutions
  /resend      - Re-broadcast latest job alert cards to the chat
  /stats       - View database and monitoring statistics
  /check       - Run live scan with real-time multi-step progress indicator
  /help        - Complete guide

Interactive Features:
  - Inline buttons for categories, sectors, and cadres
  - Interactive pagination buttons for browsing all jobs
  - Quick-search chips for one-tap searching
  - Natural text search: type any job keyword directly into chat without slashes!
"""

import sys
import io
import html
import asyncio
import logging
from telegram import (
    Update,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

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


def get_category_keyboard() -> InlineKeyboardMarkup:
    """Build interactive one-tap category selection keyboard with live counts."""
    counts = db.get_category_counts()
    kb = [
        [
            InlineKeyboardButton(f"🏛️ Govt & Central ({counts.get('govt', 0)})", callback_data="cat:govt"),
            InlineKeyboardButton(f"⚙️ Engineering ({counts.get('engineering', 0)})", callback_data="cat:engineering"),
        ],
        [
            InlineKeyboardButton(f"💻 IT & Systems ({counts.get('it', 0)})", callback_data="cat:it"),
            InlineKeyboardButton(f"⚖️ Law & Legal ({counts.get('law', 0)})", callback_data="cat:law"),
        ],
        [
            InlineKeyboardButton(f"📊 Audit & Accounts ({counts.get('audit', 0)})", callback_data="cat:audit"),
            InlineKeyboardButton(f"📈 Financial Analyst ({counts.get('analyst', 0)})", callback_data="cat:analyst"),
        ],
        [
            InlineKeyboardButton(f"🏢 Private Banks ({counts.get('private', 0)})", callback_data="cat:private"),
            InlineKeyboardButton(f"🕌 Islami Banks ({counts.get('islami', 0)})", callback_data="cat:islami"),
        ],
        [
            InlineKeyboardButton(f"💼 NBFIs & Leasing ({counts.get('nbfi', 0)})", callback_data="cat:nbfi"),
            InlineKeyboardButton(f"👔 Officers & Cadre ({counts.get('officer', 0)})", callback_data="cat:officer"),
        ],
        [
            InlineKeyboardButton(f"📚 All Active Jobs ({counts.get('total', 0)})", callback_data="page:1"),
            InlineKeyboardButton("🔍 Quick Search", callback_data="menu:search"),
        ],
    ]
    return InlineKeyboardMarkup(kb)


def get_search_keyboard() -> InlineKeyboardMarkup:
    """Build quick-search chips for instant one-tap searches."""
    kb = [
        [
            InlineKeyboardButton("🔍 Engineer", callback_data="qsearch:engineer"),
            InlineKeyboardButton("🔍 Officer", callback_data="qsearch:officer"),
            InlineKeyboardButton("🔍 IT / System", callback_data="qsearch:system"),
        ],
        [
            InlineKeyboardButton("🔍 Audit", callback_data="qsearch:audit"),
            InlineKeyboardButton("🔍 Law", callback_data="qsearch:law"),
            InlineKeyboardButton("🔍 Analyst", callback_data="qsearch:analyst"),
        ],
        [
            InlineKeyboardButton("🔍 Sonali Bank", callback_data="qsearch:sonali"),
            InlineKeyboardButton("🔍 Agrani Bank", callback_data="qsearch:agrani"),
            InlineKeyboardButton("🔍 Rupali Bank", callback_data="qsearch:rupali"),
        ],
        [
            InlineKeyboardButton("📂 Browse Categories", callback_data="menu:categories"),
            InlineKeyboardButton("📚 Browse All Jobs", callback_data="page:1"),
        ],
    ]
    return InlineKeyboardMarkup(kb)


def get_pagination_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Build interactive next/prev pagination buttons."""
    buttons = []
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️ Previous", callback_data=f"page:{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"📄 {page} / {total_pages}", callback_data="menu:noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"page:{page + 1}"))
    buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton("📂 Categories", callback_data="menu:categories"),
        InlineKeyboardButton("🔍 Search", callback_data="menu:search"),
    ])
    return InlineKeyboardMarkup(buttons)


async def send_msg(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    disable_preview: bool = True,
    reply_markup: InlineKeyboardMarkup = None,
):
    """Safely send message directly to the chat without reply_to_message_id errors."""
    try:
        chat_id = update.effective_chat.id if update.effective_chat else update.message.chat_id
        return await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=disable_preview,
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(f"Failed to send bot response: {e}")
        return None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with interactive main menu."""
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
        "👇 <b>Select an option below to get started:</b>"
    )
    await send_msg(update, context, welcome, reply_markup=get_category_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "📋 <b>Bot Commands & Shortcuts:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• /categories — One-tap category browser with live vacancy counts\n"
        "• /search [keyword] — Instant search or interactive chips\n"
        "• /latest — 5 most recent bank circulars\n"
        "• /all [page] — Browse all circulars with interactive next/prev buttons\n"
        "• /filter &lt;type&gt; — Filter by sector (govt, private, islami, nbfi)\n"
        "• /banks — View complete directory of 105+ monitored institutions\n"
        "• /check — Trigger instant scan with live 4-step progress updates\n"
        "• /stats — View database & scraper statistics\n"
        "• /resend — Re-broadcast latest alerts into the chat\n\n"
        "💡 <b>User-Friendly Tip:</b> You can also simply type any keyword directly in the chat (e.g. <i>'civil engineer'</i>, <i>'sonali bank'</i>, <i>'audit'</i>) to search immediately!"
    )
    await send_msg(update, context, help_text, reply_markup=get_category_keyboard())


async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /categories command — interactive one-tap category menu."""
    db.cleanup_expired_jobs()
    db.cleanup_duplicates()
    text = (
        "📂 <b>Bank Job Categories & Sectors</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Tap any category below to immediately view active circulars:"
    )
    await send_msg(update, context, text, reply_markup=get_category_keyboard())


async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /latest command — show 5 most recent jobs with clean card layout."""
    db.cleanup_expired_jobs()
    db.cleanup_duplicates()
    recent_jobs = db.get_recent_jobs(limit=5)
    if not recent_jobs:
        await send_msg(
            update,
            context,
            "📭 No active jobs found in database. Run <code>/check</code> to scan now!",
            reply_markup=get_category_keyboard(),
        )
        return

    await send_msg(update, context, f"📢 <b>Showing {len(recent_jobs)} Most Recent Active Bank Job Circulars:</b>")

    for job in recent_jobs:
        card = telegram_notifier.format_job_message(job)
        await send_msg(update, context, card, disable_preview=False)
        await asyncio.sleep(0.3)

    nav_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📂 Browse Categories", callback_data="menu:categories"),
            InlineKeyboardButton("📚 Browse All Jobs", callback_data="page:1"),
        ]
    ])
    await send_msg(update, context, "👉 <i>Need more? Browse by category or search below:</i>", reply_markup=nav_kb)


async def all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /all [page] — retrieve all verified jobs with interactive pagination."""
    db.cleanup_expired_jobs()
    db.cleanup_duplicates()
    page = 1
    if context.args:
        try:
            page = max(1, int(context.args[0]))
        except ValueError:
            page = 1

    await display_jobs_page(update, context, page)


async def display_jobs_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    """Display a specific page of jobs with interactive pagination buttons."""
    page_size = 5
    offset = (page - 1) * page_size
    total_jobs = db.get_job_count()
    jobs = db.get_all_jobs(limit=page_size, offset=offset, min_score=0.4)

    if not jobs:
        total_pages = max(1, (total_jobs + page_size - 1) // page_size)
        await send_msg(
            update,
            context,
            f"📭 No active jobs found on page {page}. (Total pages: {total_pages}).",
            reply_markup=get_pagination_keyboard(1, total_pages),
        )
        return

    total_pages = max(1, (total_jobs + page_size - 1) // page_size)
    header = (
        f"📚 <b>Active Banking Circulars — Page {page} of {total_pages}</b>\n"
        f"<i>({total_jobs} active circulars monitored)</i>\n"
        "───────────────────────────"
    )
    await send_msg(update, context, header)

    for job in jobs:
        card = telegram_notifier.format_job_message(job)
        await send_msg(update, context, card, disable_preview=False)
        await asyncio.sleep(0.3)

    # Attach interactive navigation buttons
    kb = get_pagination_keyboard(page, total_pages)
    await send_msg(update, context, f"<b>Page {page} of {total_pages} Navigation:</b>", reply_markup=kb)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search [keyword] command with interactive chips if query omitted."""
    db.cleanup_expired_jobs()
    db.cleanup_duplicates()

    if not context.args:
        prompt = (
            "🔍 <b>Quick Bank Job Search</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Tap any quick-search chip below, or type: <code>/search &lt;query&gt;</code>\n\n"
            "💬 <i>You can also simply type any word directly in this chat!</i>"
        )
        await send_msg(update, context, prompt, reply_markup=get_search_keyboard())
        return

    keyword = " ".join(context.args).strip()
    await execute_search(update, context, keyword)


async def execute_search(update: Update, context: ContextTypes.DEFAULT_TYPE, keyword: str):
    """Execute search query and return clean cards."""
    matches = db.search_jobs(keyword, limit=5)

    if not matches:
        await send_msg(
            update,
            context,
            f"🔍 No active bank circulars found matching '<b>{html.escape(keyword)}</b>'.\n\n"
            "Try one of the quick categories below:",
            reply_markup=get_category_keyboard(),
        )
        return

    await send_msg(update, context, f"🔍 <b>Search results for '{html.escape(keyword)}' ({len(matches)} circulars found):</b>")

    for job in matches:
        card = telegram_notifier.format_job_message(job)
        await send_msg(update, context, card, disable_preview=False)
        await asyncio.sleep(0.3)

    nav_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Another Search", callback_data="menu:search"),
            InlineKeyboardButton("📂 All Categories", callback_data="menu:categories"),
        ]
    ])
    await send_msg(update, context, "👉 <i>Explore more circulars:</i>", reply_markup=nav_kb)


async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /filter <type> (govt, private, islami, nbfi, engineering, etc.)."""
    db.cleanup_expired_jobs()
    db.cleanup_duplicates()

    if not context.args:
        await categories_command(update, context)
        return

    filter_type = context.args[0].lower().strip()
    jobs = db.get_jobs_by_category_tag(filter_type, limit=5)

    if not jobs:
        await send_msg(
            update,
            context,
            f"📭 No active jobs found for filter '<b>{html.escape(filter_type)}</b>'.\n"
            "Please select from active categories below:",
            reply_markup=get_category_keyboard(),
        )
        return

    await send_msg(update, context, f"🏷️ <b>Filter results for '{html.escape(filter_type.upper())}' ({len(jobs)} circulars):</b>")

    for job in jobs:
        card = telegram_notifier.format_job_message(job)
        await send_msg(update, context, card, disable_preview=False)
        await asyncio.sleep(0.3)

    nav_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📂 Other Categories", callback_data="menu:categories"),
            InlineKeyboardButton("🔍 Search Jobs", callback_data="menu:search"),
        ]
    ])
    await send_msg(update, context, "👉 <i>Filter another sector:</i>", reply_markup=nav_kb)


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interactive inline keyboard clicks."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "menu:noop":
        return

    if data == "menu:categories":
        text = (
            "📂 <b>Bank Job Categories & Sectors</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Tap any category below to immediately view active circulars:"
        )
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=get_category_keyboard())
        return

    if data == "menu:search":
        prompt = (
            "🔍 <b>Quick Bank Job Search</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Tap any quick-search chip below, or type your query directly in chat:"
        )
        await query.message.reply_text(prompt, parse_mode=ParseMode.HTML, reply_markup=get_search_keyboard())
        return

    if data.startswith("cat:"):
        tag = data.split(":", 1)[1]
        jobs = db.get_jobs_by_category_tag(tag, limit=5)
        display_name = tag.replace("_", " ").title()

        if not jobs:
            await query.message.reply_text(
                f"📭 No active circulars currently found in category '<b>{html.escape(display_name)}</b>'.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_category_keyboard(),
            )
            return

        await query.message.reply_text(
            f"📂 <b>Showing {len(jobs)} Active Circulars for '{html.escape(display_name)}':</b>",
            parse_mode=ParseMode.HTML,
        )
        for job in jobs:
            card = telegram_notifier.format_job_message(job)
            await query.message.reply_text(card, parse_mode=ParseMode.HTML, disable_web_page_preview=False)
            await asyncio.sleep(0.3)

        nav_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📂 Other Categories", callback_data="menu:categories"),
                InlineKeyboardButton("🔍 Search Jobs", callback_data="menu:search"),
            ]
        ])
        await query.message.reply_text("👉 <i>Need more? Browse another category:</i>", reply_markup=nav_kb)
        return

    if data.startswith("qsearch:"):
        term = data.split(":", 1)[1]
        await execute_search(update, context, term)
        return

    if data.startswith("page:"):
        try:
            page = int(data.split(":", 1)[1])
            await display_jobs_page(update, context, page)
        except ValueError:
            pass
        return


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Intelligent natural text query handler:
    When user types plain text (e.g. 'engineer', 'sonali bank', 'audit', 'officer'),
    automatically performs a search!
    """
    text = (update.message.text or "").strip()
    if not text or text.startswith("/"):
        return

    # Trigger smart search for the user's input
    logger.info(f"Natural text query received: '{text}'")
    await execute_search(update, context, text)


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
            f"⏳ <b>[2/4]</b> 🏦 <i>BB e-Recruitment checked ({len(bb_jobs)} circulars). Scanning 105+ banks & NBFIs...</i>",
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
            f"👉 Type <code>/latest</code> or <code>/categories</code> to browse anytime!"
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
        BotCommand("categories", "One-tap category browser with live counts"),
        BotCommand("search", "Instant search or quick-search chips"),
        BotCommand("all", "Browse all circulars with interactive next/prev buttons"),
        BotCommand("filter", "Filter by sector or cadre"),
        BotCommand("banks", "List all 105+ monitored banks & NBFIs"),
        BotCommand("check", "Run instant scrape with progress indicator"),
        BotCommand("stats", "View database & monitoring statistics"),
        BotCommand("resend", "Re-broadcast latest job alerts to chat"),
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

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("categories", categories_command))
    app.add_handler(CommandHandler("category", categories_command))
    app.add_handler(CommandHandler("latest", latest_command))
    app.add_handler(CommandHandler("all", all_command))
    app.add_handler(CommandHandler("jobs", all_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("filter", filter_command))
    app.add_handler(CommandHandler("banks", banks_command))
    app.add_handler(CommandHandler("resend", resend_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("check", check_command))

    # Interactive callback query handler (inline buttons click)
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Natural text message handler (search any keyword without typing slashes)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    print("✅ Bot is online with interactive categories, quick search chips & pagination buttons!")
    app.run_polling(poll_interval=0.5, timeout=10, drop_pending_updates=True)


if __name__ == "__main__":
    main()
