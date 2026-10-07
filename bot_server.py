"""
Interactive Telegram Bot Server & 30-Minute Autonomous Monitor
==============================================================
Commands (Clean & Deduplicated):
  /fetchall    - Retrieve & deliver ALL circulars from database (restores chat history)
  /latest      - 5 most recent verified banking circulars
  /categories  - One-tap category browser with live counts (Govt, IT, Engineering, Law, etc.)
  /search      - Search by keyword or tap quick-search chips
  /scan        - Trigger live scan now across all 105+ institutions with progress bar
  /banks       - View complete directory of 105+ monitored banks & NBFIs
  /stats       - View database & monitoring metrics
  /help        - Command guide & instructions

Autonomous Features:
  - 30-Minute Monitoring Engine: automatically checks BB BSCS + all 105+ banks & NBFIs
  - Automated Smart Deletion: purges expired jobs and blacklists them permanently
  - Cross-Source Deduplication: merges duplicate circulars while preserving cadres
  - Broadcast Engine: automatically sends any new circulars to Telegram
"""

import os
import sys
import io
import html
import asyncio
import logging
import subprocess
import threading
from datetime import datetime
from telegram import (
    Update,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
    BotCommandScopeAllGroupChats,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ChatMemberHandler,
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

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_OWNER_ID
from config.banks import BANKS, ALL_SOURCES
from storage.database import Database
from scrapers.bb_erecruitment_scraper import BBErecruitmentScraper
from scrapers.career_page_scraper import CareerPageScraper
from scrapers.bdjobs_scraper import BdjobsScraper
from scrapers.portal_scraper import PortalScraper
from ai.job_analyzer import JobAnalyzer
from notifiers.telegram_bot import TelegramNotifier

db = Database()
telegram_notifier = TelegramNotifier()


def get_guest_commands() -> list[BotCommand]:
    """Commands visible only to non-approved guests/members."""
    return [
        BotCommand("start", "Start bot & welcome menu"),
        BotCommand("requestaccess", "Request 1-on-1 bot usage or group invite"),
        BotCommand("help", "Help guide & instructions"),
    ]


def get_member_commands() -> list[BotCommand]:
    """Commands visible to approved members and group participants (no /mode, /requests, /requestaccess)."""
    return [
        BotCommand("start", "Start bot & interactive menu"),
        BotCommand("fetchall", "Deliver ALL active circulars (chat recovery)"),
        BotCommand("latest", "5 most recent verified circulars"),
        BotCommand("categories", "One-tap category browser with live counts"),
        BotCommand("search", "Instant position search"),
        BotCommand("scan", "Live scan across 105+ sources"),
        BotCommand("banks", "List all 105+ monitored institutions"),
        BotCommand("stats", "Database & monitoring metrics"),
        BotCommand("help", "Bot command guide"),
    ]


def get_primary_owner_commands() -> list[BotCommand]:
    """Commands visible exclusively to the Primary Bot Owner (includes /permissions, /mode, /requests)."""
    return [
        BotCommand("start", "Start bot & interactive menu"),
        BotCommand("permissions", "Owner: Grant / Revoke owner command permissions"),
        BotCommand("mode", "Owner: Toggle 1-on-1 Bot Public / Private"),
        BotCommand("requests", "Owner: Review & approve access requests"),
        BotCommand("fetchall", "Deliver ALL active circulars (chat recovery)"),
        BotCommand("latest", "5 most recent verified circulars"),
        BotCommand("categories", "One-tap category browser with live counts"),
        BotCommand("search", "Instant position search"),
        BotCommand("scan", "Live scan across 105+ sources"),
        BotCommand("banks", "List all 105+ monitored institutions"),
        BotCommand("stats", "Database & monitoring metrics"),
        BotCommand("help", "Owner command guide"),
    ]


def get_delegated_owner_commands() -> list[BotCommand]:
    """Commands visible to delegated users granted owner permission (includes /mode and /requests, NO /permissions)."""
    return [
        BotCommand("start", "Start bot & interactive menu"),
        BotCommand("mode", "Toggle 1-on-1 Bot Public / Private"),
        BotCommand("requests", "Review & approve access requests"),
        BotCommand("fetchall", "Deliver ALL active circulars (chat recovery)"),
        BotCommand("latest", "5 most recent verified circulars"),
        BotCommand("categories", "One-tap category browser with live counts"),
        BotCommand("search", "Instant position search"),
        BotCommand("scan", "Live scan across 105+ sources"),
        BotCommand("banks", "List all 105+ monitored institutions"),
        BotCommand("stats", "Database & monitoring metrics"),
        BotCommand("help", "Bot command guide"),
    ]


def get_owner_commands() -> list[BotCommand]:
    """Alias for primary owner commands."""
    return get_primary_owner_commands()


def sync_website_data(commit_message: str = "chore(sync): update jobs and access mode"):
    """
    Export fresh data/jobs.json and auto-push to GitHub in the background
    so GitHub Pages immediately reflects the live status without manual intervention.
    """
    try:
        import export_web_data
        export_web_data.export_all()

        def _push_worker():
            try:
                subprocess.run(["git", "add", "data/jobs.json"], capture_output=True, text=True, check=True)
                diff_check = subprocess.run(["git", "diff", "--staged", "--name-only"], capture_output=True, text=True)
                if "data/jobs.json" in diff_check.stdout:
                    subprocess.run(["git", "commit", "-m", commit_message], capture_output=True, text=True, check=True)
                    subprocess.run(["git", "push", "origin", "master"], capture_output=True, text=True, check=True)
                    logger.info(f"✅ Auto-synced jobs.json to GitHub Pages: {commit_message}")
            except Exception as push_err:
                logger.warning(f"Background git push skipped or error: {push_err}")

        threading.Thread(target=_push_worker, daemon=True).start()
    except Exception as err:
        logger.error(f"Error in sync_website_data: {err}")


def get_category_keyboard() -> InlineKeyboardMarkup:
    """Build interactive one-tap category selection keyboard with live vacancy counts."""
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
            InlineKeyboardButton(f"📚 All Active Circulars ({counts.get('total', 0)})", callback_data="menu:fetchall"),
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
            InlineKeyboardButton("📚 Fetch All Circulars", callback_data="menu:fetchall"),
        ],
    ]
    return InlineKeyboardMarkup(kb)


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


async def is_primary_owner(user_id: str, context: ContextTypes.DEFAULT_TYPE = None) -> bool:
    """
    Check if user_id is the primary root bot owner.
    ONLY the primary owner can view/execute /permissions, /grant, /revoke.
    """
    if not user_id:
        return False
    user_str = str(user_id).strip()

    # 1. Matches TELEGRAM_OWNER_ID config
    owner_conf = str(TELEGRAM_OWNER_ID).strip()
    if owner_conf and user_str == owner_conf:
        return True

    # 2. Telegram group creator check
    if context and TELEGRAM_CHAT_ID:
        try:
            admins = await context.bot.get_chat_administrators(int(TELEGRAM_CHAT_ID))
            for a in admins:
                if a.status == "creator" and str(a.user.id) == user_str:
                    return True
        except Exception:
            pass

    return False


async def can_manage_owner_commands(user_id: str, context: ContextTypes.DEFAULT_TYPE = None) -> bool:
    """
    Check if user can view/execute owner-level commands (/mode, /requests, approve/reject).
    Allowed if user is primary owner OR has been granted owner permission via /grant or /permissions.
    """
    if not user_id:
        return False
    user_str = str(user_id).strip()

    if await is_primary_owner(user_str, context):
        return True

    return db.has_owner_permission(user_str)


async def is_owner(user_id: str, context: ContextTypes.DEFAULT_TYPE = None) -> bool:
    """Check if user_id is the bot owner (creator). Backwards compatibility alias."""
    return await is_primary_owner(user_id, context)


async def is_admin(user_id: str, context: ContextTypes.DEFAULT_TYPE = None) -> bool:
    """Check if user_id is an administrator or owner."""
    if not user_id:
        return False
    user_str = str(user_id).strip()

    if await is_owner(user_str, context):
        return True

    # 1. Environment variable TELEGRAM_ADMIN_IDS
    admin_env = os.getenv("TELEGRAM_ADMIN_IDS", "")
    admin_set = {aid.strip() for aid in admin_env.split(",") if aid.strip()}
    if user_str in admin_set:
        return True

    # 2. Match with personal TELEGRAM_CHAT_ID (if user chat)
    if user_str == str(TELEGRAM_CHAT_ID):
        return True

    # 3. Database authorized_users with access_type='admin'
    admin_users = [
        u["user_id"] for u in db.list_authorized_users(status="approved")
        if u.get("access_type") == "admin"
    ]
    if user_str in admin_users:
        return True

    # 4. Group administrators query
    if context and TELEGRAM_CHAT_ID:
        try:
            admins = await context.bot.get_chat_administrators(int(TELEGRAM_CHAT_ID))
            for a in admins:
                if str(a.user.id) == user_str:
                    return True
        except Exception:
            pass

    return False


def is_authorized(update: Update) -> bool:
    """
    Check if update is authorized based on current mode and approval status.
    - Groups: ONLY the official TELEGRAM_CHAT_ID group is allowed. All other groups are blocked.
    - 1-on-1 DMs:
      - Owner: always authorized.
      - If in PUBLIC mode: all users can query.
      - If in PRIVATE mode: requires approved bot usage or admin.
    """
    if not update.effective_chat:
        return False

    chat_id = str(update.effective_chat.id)
    chat_type = update.effective_chat.type  # 'private', 'group', 'supergroup'
    user_id = str(update.effective_user.id) if update.effective_user else ""

    # Group chats: strictly restricted to official group only under all circumstances
    if chat_type in ["group", "supergroup"]:
        return chat_id == str(TELEGRAM_CHAT_ID)

    # Owner or user with delegated owner permission is always authorized
    if user_id:
        user_str = str(user_id).strip()
        if user_str == str(TELEGRAM_OWNER_ID).strip() or db.has_owner_permission(user_str):
            return True

    # 1-on-1 Private DMs:
    mode = db.get_access_mode()
    if mode == "public":
        return True

    # In PRIVATE mode for 1-on-1:
    admin_env = os.getenv("TELEGRAM_ADMIN_IDS", "")
    if admin_env:
        for aid in admin_env.split(","):
            if aid.strip() and user_id == aid.strip():
                return True

    if user_id and db.is_user_authorized(user_id):
        return True

    return False


def get_access_request_keyboard() -> InlineKeyboardMarkup:
    """Keyboard allowing users to choose between Bot Usage Permission or Group Invite."""
    kb = [
        [
            InlineKeyboardButton("🤖 Request Bot Usage Permission (1-on-1)", callback_data="req_access:bot"),
        ],
        [
            InlineKeyboardButton("👥 Request Private Group Invite Link", callback_data="req_access:group"),
        ],
    ]
    return InlineKeyboardMarkup(kb)


async def enforce_private_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Privacy & Access Gateway:
    - In PUBLIC mode: permits all queries.
    - In PRIVATE mode: permits authorized members/group. For others, offers
      direct join request / bot usage permission request toggle.
    """
    if is_authorized(update):
        return True

    # Permit request access and admin callback buttons to pass through
    if update.callback_query:
        data = update.callback_query.data or ""
        if (
            data.startswith("req_access:")
            or data.startswith("adm_app:")
            or data.startswith("adm_rej:")
            or data.startswith("set_mode:")
        ):
            return True
        await update.callback_query.answer("🔒 Private Bot: Please tap below to request access permission.", show_alert=True)
        return False

    sender = update.effective_user.username if (update.effective_user and update.effective_user.username) else "unknown"
    chat_id = update.effective_chat.id if update.effective_chat else "unknown"
    user_id = str(update.effective_user.id) if update.effective_user else ""
    logger.info(f"Unapproved access attempt: user=@{sender} (ID: {user_id}), chat_id={chat_id}")

    prompt = (
        "🔒 <b>BD Bank Jobs AI — Private Mode Active</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "This bot is currently in <b>Private Mode</b> to maintain high alert fidelity and prevent spam.\n\n"
        "👉 <b>Choose an access option below to request permission:</b>\n\n"
        "• <b>🤖 Bot Usage Permission:</b>\n"
        "  Gain permission to use the bot directly in this 1-on-1 private chat <i>without joining any group</i>.\n\n"
        "• <b>👥 Private Group Invite:</b>\n"
        "  Receive an exclusive admin-approved invitation to join the official alert community for 30-min broadcasts.\n\n"
        "<i>Tap an option below. Your request will be instantly forwarded to the administrator:</i>"
    )

    if update.message:
        await update.message.reply_text(prompt, parse_mode=ParseMode.HTML, reply_markup=get_access_request_keyboard())
    return False


async def on_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Automatically leave any group that is not the approved TELEGRAM_CHAT_ID.
    Prevents unauthorized groups from adding the bot.
    """
    chat = update.effective_chat
    if not chat:
        return
    if str(chat.id) != str(TELEGRAM_CHAT_ID):
        logger.warning(f"Bot added to unauthorized group '{chat.title}' ({chat.id}). Auto-leaving immediately...")
        try:
            await context.bot.leave_chat(chat.id)
        except Exception as e:
            logger.error(f"Error leaving unauthorized chat {chat.id}: {e}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with interactive main menu."""
    if not await enforce_private_access(update, context):
        return

    welcome = (
        "🏦 <b>Bangladesh Bank & Financial Sector Job Monitor</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Autonomous monitoring of <b>105+ banks & financial institutions</b> across Bangladesh:\n"
        "• 🏛️ <b>Govt & Central Bank:</b> Bangladesh Bank (BSCS), Sonali, Janata, Agrani, Rupali, BASIC, BDBL, BKB, RAKUB, PKB\n"
        "• 🏢 <b>Private Commercial (33):</b> BRAC, City, EBL, MTB, Prime, Bank Asia, DBBL, IFIC, Jamuna, etc.\n"
        "• 🕌 <b>Islami Shariah (10):</b> IBBL, Al-Arafah, SIBL, SJIBL, EXIM, Union, Global Islami, etc.\n"
        "• 🌍 <b>Foreign & Digital (11):</b> Standard Chartered, HSBC, Woori, Nagad Digital, Kori Digital, etc.\n"
        "• 💼 <b>NBFIs (35):</b> IDLC, IPDC, LankaBangla, DBH, United Finance, IDCOL, etc.\n"
        "• 🌐 <b>Portals:</b> Bangladesh Bank e-Recruitment, Bdjobs, Skill Jobs\n\n"
        "⏱️ <i>Scans automatically every 30 minutes in the background!</i>\n\n"
        "👇 <b>Select an option below to get started:</b>"
    )
    await send_msg(update, context, welcome, reply_markup=get_category_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command with role-tailored guide."""
    user_id = str(update.effective_user.id) if update.effective_user else ""
    is_primary = await is_primary_owner(user_id, context)
    can_manage = await can_manage_owner_commands(user_id, context)

    # For non-approved guests in private chat
    if not is_authorized(update) and not is_primary and not can_manage:
        guest_help = (
            "📋 <b>BD Bank Jobs AI — Guest Guide:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• <code>/start</code> — Welcome menu & access overview\n"
            "• <code>/requestaccess</code> — Request 1-on-1 bot usage or private group invite\n\n"
            "<i>To unlock full query commands (/latest, /fetchall, /categories, /search), submit a request using <code>/requestaccess</code>.</i>"
        )
        await send_msg(update, context, guest_help)
        return

    help_text = (
        "📋 <b>Bot Commands Guide:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "• <code>/fetchall</code> — <b>Retrieve and deliver ALL circulars</b> from database (use anytime if you deleted chat!)\n"
        "• <code>/latest</code> — Show 5 most recent verified banking circulars\n"
        "• <code>/categories</code> — One-tap category browser with live counts\n"
        "• <code>/search [keyword]</code> — Instant search or one-click search chips\n"
        "• <code>/scan</code> — Trigger live scan now across all 105+ institutions with progress updates\n"
        "• <code>/banks</code> — View complete directory of 105+ monitored institutions\n"
        "• <code>/stats</code> — View database and monitoring metrics\n\n"
        "💡 <b>Tip:</b> You can also type any keyword directly in chat (e.g., <i>'civil engineer'</i>, <i>'sonali bank'</i>, <i>'audit'</i>) to search immediately!"
    )

    if is_primary:
        help_text += (
            "\n\n👑 <b>Primary Owner Controls:</b>\n"
            "• <code>/permissions</code> — Manage owner-level command permissions for users\n"
            "• <code>/grant &lt;user_id&gt;</code> — Grant owner commands to user\n"
            "• <code>/revoke &lt;user_id&gt;</code> — Revoke owner commands from user\n"
            "• <code>/mode [public|private]</code> — Toggle 1-on-1 Bot access mode & sync website\n"
            "• <code>/requests</code> — Review & approve/reject pending access requests"
        )
    elif can_manage:
        help_text += (
            "\n\n⭐ <b>Owner Commands (Delegated Access):</b>\n"
            "• <code>/mode [public|private]</code> — Toggle 1-on-1 Bot access mode & sync website\n"
            "• <code>/requests</code> — Review & approve/reject pending access requests"
        )

    await send_msg(update, context, help_text, reply_markup=get_category_keyboard())


async def fetchall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /fetchall (also /fetch_all, /resend_all, /all).
    Delivers ALL active circulars from the database to restore entire chat history!
    """
    if not await enforce_private_access(update, context):
        return

    db.cleanup_expired_jobs()
    db.cleanup_duplicates()
    all_jobs = db.get_all_jobs(limit=100, min_score=0.4)

    if not all_jobs:
        await send_msg(
            update,
            context,
            "📭 No active circulars currently in the database. Run <code>/scan</code> to scan now!",
            reply_markup=get_category_keyboard(),
        )
        return

    header = (
        f"🔄 <b>Delivering All Active Circulars from Database...</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>({len(all_jobs)} verified positions currently active. Sending all cards now):</i>"
    )
    await send_msg(update, context, header)

    for idx, job in enumerate(all_jobs, 1):
        card = telegram_notifier.format_job_message(job)
        await send_msg(update, context, card, disable_preview=False)
        await asyncio.sleep(0.4)  # Rate limit protection

    footer = (
        f"✅ <b>Delivered all {len(all_jobs)} active circulars!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>All 105+ banks & financial institutions are monitored every 30 minutes.</i>"
    )
    await send_msg(update, context, footer, reply_markup=get_category_keyboard())


async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /latest command — show 5 most recent jobs with clean card layout."""
    if not await enforce_private_access(update, context):
        return

    db.cleanup_expired_jobs()
    db.cleanup_duplicates()
    recent_jobs = db.get_recent_jobs(limit=5)
    if not recent_jobs:
        await send_msg(
            update,
            context,
            "📭 No active jobs found in database. Run <code>/scan</code> to scan now!",
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
            InlineKeyboardButton("📚 Fetch All Circulars", callback_data="menu:fetchall"),
            InlineKeyboardButton("📂 Browse Categories", callback_data="menu:categories"),
        ]
    ])
    await send_msg(update, context, "👉 <i>Need all circulars or more categories?</i>", reply_markup=nav_kb)


async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /categories command — interactive one-tap category menu."""
    if not await enforce_private_access(update, context):
        return

    db.cleanup_expired_jobs()
    db.cleanup_duplicates()
    text = (
        "📂 <b>Bank Job Categories & Disciplines</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Tap any category below to immediately view active circulars:"
    )
    await send_msg(update, context, text, reply_markup=get_category_keyboard())


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search [keyword] command with interactive chips if query omitted."""
    if not await enforce_private_access(update, context):
        return

    db.cleanup_expired_jobs()
    db.cleanup_duplicates()

    if not context.args:
        prompt = (
            "🔍 <b>Quick Bank Job Search</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Tap any quick-search chip below, or type: <code>/search &lt;query&gt;</code>\n\n"
            "💬 <i>You can also simply type any keyword directly in this chat!</i>"
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
            "Try one of the active categories below:",
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


async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /scan (or /check) — on-demand scrape with live progress indication."""
    if not await enforce_private_access(update, context):
        return

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

        # Step 2: All 105+ Bank Career Pages & NBFIs
        await status_msg.edit_text(
            f"⏳ <b>[2/5]</b> 🏦 <i>BB e-Recruitment checked ({len(bb_jobs)} circulars). Scanning 104+ banks & NBFIs in parallel...</i>",
            parse_mode=ParseMode.HTML,
        )

        career_scraper = CareerPageScraper()
        sources = [s for s in BANKS if s.get("short_name") != "BB_BSCS" and s.get("enabled", True)]
        bank_jobs = await asyncio.to_thread(career_scraper.scrape_all_concurrent, sources, 15)
        total_career_new = 0
        for j in bank_jobs:
            if db.insert_job(j) is not None:
                total_career_new += 1

        # Step 3: All 5 Modern Job Portals & Aggregators (Bdjobs, LinkedIn, BDJobsToday, Chakrir Khobor, Skill Jobs)
        await status_msg.edit_text(
            f"⏳ <b>[3/5]</b> 🌐 <i>Bank careers scanned ({total_career_new} new). Checking 5 Portals (Bdjobs, LinkedIn, BDJobsToday, Chakrir Khobor, Skill Jobs)...</i>",
            parse_mode=ParseMode.HTML,
        )

        bdjobs_scraper = BdjobsScraper()
        portal_scraper = PortalScraper()
        portal_jobs = await asyncio.to_thread(lambda: bdjobs_scraper.scrape_all_categories() + portal_scraper.scrape_all_portals())
        total_portal_new = 0
        for j in portal_jobs:
            if db.insert_job(j) is not None:
                total_portal_new += 1

        # Step 4: AI Analysis
        total_new = new_bb + total_career_new + total_portal_new
        await status_msg.edit_text(
            f"⏳ <b>[4/5]</b> 🧠 <i>Scraping complete ({total_new} new jobs found). Running Gemini AI analysis...</i>",
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

        # Step 5: Notifications
        await status_msg.edit_text(
            f"⏳ <b>[5/5]</b> 📬 <i>AI analysis complete ({analyzed_count} analyzed). Delivering notifications...</i>",
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
            f"• 🏦 <b>Bank Career Pages Scanned:</b> {len(sources)} institutions\n"
            f"• 🌐 <b>Job Portals & Aggregators:</b> Bdjobs, LinkedIn, BDJobsToday, Chakrir Khobor, Skill Jobs ({len(portal_jobs)} verified)\n"
            f"• 🆕 <b>New Jobs Discovered:</b> {total_new}\n"
            f"• 🧠 <b>Jobs Analyzed by AI:</b> {analyzed_count}\n"
            f"• 📢 <b>Notifications Delivered:</b> {sent_count}\n\n"
            f"👉 Type <code>/fetchall</code> to view all circulars anytime!"
        )
        await status_msg.edit_text(summary_text, parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error during on-demand check: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Error during scan:</b> <code>{html.escape(str(e)[:250])}</code>",
            parse_mode=ParseMode.HTML,
        )


async def banks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /banks — list monitored banks and institutions."""
    if not await enforce_private_access(update, context):
        return

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
        "🌐 <b>Recruitment Portals:</b>\n"
        "• Bangladesh Bank e-Recruitment (BSCS)\n"
        "• bdjobs.com (Banking & NBFI categories)\n"
        "• Skill Jobs (Banking category)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>All monitored continuously every 30 minutes!</i>"
    )
    await send_msg(update, context, text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command."""
    if not await enforce_private_access(update, context):
        return

    total_jobs = db.get_job_count()
    scrape_stats = db.get_scrape_stats()

    stats_msg = (
        "📊 <b>BD Bank Job Monitor — Statistics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Total Active Circulars:</b> {total_jobs}\n"
        f"• <b>Monitored Institutions:</b> {len(BANKS)} Organizations\n"
        f"• <b>Scan Interval:</b> Every 30 Minutes (Continuous)\n"
        f"• <b>Total Scrape Runs:</b> {scrape_stats.get('total_scrapes', 0)}\n"
        f"• <b>Successful Scrapes:</b> {scrape_stats.get('successful', 0)}\n"
        f"• <b>New Jobs Discovered:</b> {scrape_stats.get('total_new_jobs', 0)}\n\n"
        "🤖 <i>Status: Fully Active & Monitoring 24/7</i>"
    )
    await send_msg(update, context, stats_msg)


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command to view and toggle 1-on-1 Bot Usage between PUBLIC and PRIVATE mode."""
    user_id = str(update.effective_user.id) if update.effective_user else ""
    if not await can_manage_owner_commands(user_id, context):
        await send_msg(update, context, "⛔ <b>Access Denied:</b> The <code>/mode</code> command is restricted to the bot owner and delegated managers.")
        return

    # Check for direct argument: /mode public or /mode private
    if context.args:
        arg = context.args[0].lower().strip()
        new_mode = None
        if arg in ["public", "open", "pub"]:
            new_mode = "public"
        elif arg in ["private", "restricted", "priv"]:
            new_mode = "private"

        if new_mode:
            db.set_access_mode(new_mode)
            sync_website_data(f"chore(mode): set 1-on-1 bot access mode to {new_mode}")

            status_text = (
                "🌐 <b>PUBLIC MODE ACTIVATED</b>\n"
                "• <b>1-on-1 Bot Usage:</b> Open to all Telegram users without prior approval.\n"
                "• <b>Private Group:</b> Unaffected (strictly invite-only with admin clearance).\n"
                "• <b>Website:</b> Status indicator updated to <b>Public (Open)</b>."
                if new_mode == "public" else
                "🔒 <b>PRIVATE MODE ACTIVATED</b>\n"
                "• <b>1-on-1 Bot Usage:</b> Restricted to approved users only. Outsiders must request approval.\n"
                "• <b>Private Group:</b> Unaffected (strictly invite-only with admin clearance).\n"
                "• <b>Website:</b> Status indicator updated to <b>Private (Approval Gated)</b>."
            )
            await send_msg(update, context, f"✅ <b>1-on-1 Access Mode Updated!</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{status_text}")
            return

    current_mode = db.get_access_mode()
    mode_text = "🔒 <b>PRIVATE (Approval Required for 1-on-1 Bot DM)</b>" if current_mode == "private" else "🌐 <b>PUBLIC (Open 1-on-1 Bot DM)</b>"

    kb = [
        [
            InlineKeyboardButton("🌐 Set 1-on-1 Bot: PUBLIC", callback_data="set_mode:public"),
            InlineKeyboardButton("🔒 Set 1-on-1 Bot: PRIVATE", callback_data="set_mode:private"),
        ]
    ]
    msg = (
        "⚙️ <b>1-on-1 Bot Usage Access Mode</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Current Active Mode:</b> {mode_text}\n"
        "• <b>Private Group Access:</b> Strictly Private & Admin-Gated under all modes\n\n"
        "<b>Usage Overview:</b>\n"
        "• <b>🔒 PRIVATE:</b> Direct 1-on-1 bot usage requires admin approval. Website reflects Private status.\n"
        "• <b>🌐 PUBLIC:</b> Anyone on Telegram can query circulars 1-on-1 immediately. Website reflects Public status.\n\n"
        "<i>Tap a button below or type <code>/mode public</code> or <code>/mode private</code>:</i>"
    )
    await send_msg(update, context, msg, reply_markup=InlineKeyboardMarkup(kb))


async def requests_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner command to view and review pending access requests."""
    user_id = str(update.effective_user.id) if update.effective_user else ""
    if not await can_manage_owner_commands(user_id, context):
        await send_msg(update, context, "⛔ <b>Access Denied:</b> The <code>/requests</code> command is restricted to the bot owner and delegated managers.")
        return


async def permissions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    PRIMARY OWNER ONLY: View and manage owner-level command permissions.
    Allows delegating /mode and /requests execution to other trusted users.
    """
    user_id = str(update.effective_user.id) if update.effective_user else ""
    if not await is_primary_owner(user_id, context):
        await send_msg(update, context, "⛔ <b>Access Denied:</b> The <code>/permissions</code> command is restricted exclusively to the primary bot owner.")
        return

    delegated = db.list_delegated_owners()
    approved = db.list_authorized_users(status="approved")

    text = (
        "👑 <b>Owner Command Permissions Management</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "As the primary bot owner, you can grant or revoke permission for trusted users "
        "to see and execute owner-level commands (<code>/mode</code> and <code>/requests</code>).\n\n"
        "<b>👥 Currently Delegated Users:</b>\n"
    )

    if delegated:
        for u in delegated:
            uname = f"@{u['username']}" if u.get("username") else "no_username"
            fname = u.get("full_name") or "User"
            uid = u["user_id"]
            text += f"• 👤 <b>{html.escape(fname)}</b> ({uname}) — ID: <code>{uid}</code>\n"
    else:
        text += "• <i>No delegated users currently. Only you (Primary Owner) have access to owner commands.</i>\n"

    text += (
        "\n<b>⚙️ Delegation Commands:</b>\n"
        "• <code>/grant &lt;user_id&gt;</code> — Grant owner commands (/mode, /requests) to user\n"
        "• <code>/revoke &lt;user_id&gt;</code> — Revoke owner commands from user\n\n"
        "<i>Or tap an action button below:</i>"
    )

    kb = []
    # Add buttons to revoke currently delegated users
    for u in delegated:
        uname = u.get("username") or u.get("full_name") or u["user_id"]
        kb.append([
            InlineKeyboardButton(f"❌ Revoke: {uname} ({u['user_id']})", callback_data=f"perm_rev:{u['user_id']}")
        ])

    # Add buttons for other approved users to grant
    delegated_ids = {str(u["user_id"]) for u in delegated}
    non_delegated = [
        u for u in approved 
        if str(u["user_id"]) not in delegated_ids and str(u["user_id"]) != str(TELEGRAM_OWNER_ID)
    ]
    for u in non_delegated[:6]:
        uname = u.get("username") or u.get("full_name") or u["user_id"]
        kb.append([
            InlineKeyboardButton(f"➕ Grant: {uname} ({u['user_id']})", callback_data=f"perm_grant:{u['user_id']}")
        ])

    reply_markup = InlineKeyboardMarkup(kb) if kb else None
    await send_msg(update, context, text, reply_markup=reply_markup)


async def grant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """PRIMARY OWNER ONLY: Grant owner commands (/mode, /requests) to a user ID."""
    user_id = str(update.effective_user.id) if update.effective_user else ""
    if not await is_primary_owner(user_id, context):
        await send_msg(update, context, "⛔ <b>Access Denied:</b> Only the primary bot owner can grant command permissions.")
        return

    if not context.args:
        await send_msg(
            update,
            context,
            "⚠️ <b>Usage:</b> <code>/grant &lt;user_id&gt;</code>\n"
            "Example: <code>/grant 123456789</code>\n\n"
            "<i>Use <code>/permissions</code> to view all users.</i>"
        )
        return

    target_uid = context.args[0].replace("@", "").strip()
    if not target_uid.isdigit():
        await send_msg(update, context, "⚠️ <b>Invalid User ID:</b> Please provide a numeric Telegram User ID.")
        return

    db.grant_owner_permission(target_uid, granted_by=user_id)

    # Dynamically update the target user's Telegram command menu scope
    try:
        await context.bot.set_my_commands(
            get_delegated_owner_commands(),
            scope=BotCommandScopeChat(chat_id=int(target_uid))
        )
    except Exception as e:
        logger.warning(f"Could not update scoped commands for granted user {target_uid}: {e}")

    # Notify target user in Telegram DM
    try:
        await context.bot.send_message(
            chat_id=int(target_uid),
            text=(
                "🎉 <b>Owner Command Permissions Granted!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "The bot owner has granted you permission to view and execute owner commands:\n"
                "• <code>/mode</code> — Toggle 1-on-1 Bot Public / Private & sync website\n"
                "• <code>/requests</code> — Review and approve user access requests\n\n"
                "Your Telegram command menu has been updated with these commands!"
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass

    await send_msg(
        update,
        context,
        f"✅ <b>Permissions Granted!</b>\n"
        f"User <code>{target_uid}</code> has been granted owner command permissions.\n"
        f"Their Telegram command menu has been updated with <code>/mode</code> and <code>/requests</code>."
    )


async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """PRIMARY OWNER ONLY: Revoke owner commands from a user ID."""
    user_id = str(update.effective_user.id) if update.effective_user else ""
    if not await is_primary_owner(user_id, context):
        await send_msg(update, context, "⛔ <b>Access Denied:</b> Only the primary bot owner can revoke command permissions.")
        return

    if not context.args:
        await send_msg(
            update,
            context,
            "⚠️ <b>Usage:</b> <code>/revoke &lt;user_id&gt;</code>\n"
            "Example: <code>/revoke 123456789</code>\n\n"
            "<i>Use <code>/permissions</code> to view all delegated users.</i>"
        )
        return

    target_uid = context.args[0].replace("@", "").strip()
    if not target_uid.isdigit():
        await send_msg(update, context, "⚠️ <b>Invalid User ID:</b> Please provide a numeric Telegram User ID.")
        return

    db.revoke_owner_permission(target_uid)

    # Revert target user's Telegram command menu scope to standard member commands
    try:
        await context.bot.set_my_commands(
            get_member_commands(),
            scope=BotCommandScopeChat(chat_id=int(target_uid))
        )
    except Exception as e:
        logger.warning(f"Could not revert scoped commands for revoked user {target_uid}: {e}")

    # Notify target user in Telegram DM
    try:
        await context.bot.send_message(
            chat_id=int(target_uid),
            text=(
                "ℹ️ <b>Permission Update:</b>\n"
                "Your owner command permissions (<code>/mode</code>, <code>/requests</code>) have been revoked by the bot owner."
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception:
        pass

    await send_msg(
        update,
        context,
        f"✅ <b>Permissions Revoked!</b>\n"
        f"User <code>{target_uid}</code> no longer has owner command access.\n"
        f"Their Telegram menu has been reset to standard member commands."
    )

    pending = db.list_authorized_users(status="pending")
    if not pending:
        await send_msg(update, context, "✅ <b>No pending access requests.</b> All requests have been reviewed.")
        return

    await send_msg(update, context, f"📋 <b>Found {len(pending)} Pending Access Requests:</b>")
    for req in pending[:10]:
        uid = req["user_id"]
        uname = req.get("username") or "no_username"
        fname = req.get("full_name") or "User"
        atype = req.get("access_type") or "bot"
        type_label = "Bot Usage Permission" if atype == "bot" else "Group Membership"

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"✅ Approve ({type_label})", callback_data=f"adm_app:{atype}:{uid}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"adm_rej:{uid}"),
            ]
        ])
        card = (
            f"👤 <b>{html.escape(fname)}</b> (@{uname})\n"
            f"🆔 User ID: <code>{uid}</code>\n"
            f"🎯 Request Type: <b>{type_label}</b>\n"
            f"📅 Submitted: {req.get('updated_at', 'recently')}"
        )
        await send_msg(update, context, card, reply_markup=kb)
        await asyncio.sleep(0.2)


async def request_access_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bring up the access request menu for unauthorized / non-approved members."""
    user_id = str(update.effective_user.id) if update.effective_user else ""
    chat_id = str(update.effective_chat.id) if update.effective_chat else ""

    if await is_owner(user_id, context):
        await send_msg(update, context, "👑 <b>Bot Owner:</b> You have full root access to all bot features and commands.")
        return

    if db.is_user_authorized(user_id) or chat_id == str(TELEGRAM_CHAT_ID):
        await send_msg(update, context, "✅ <b>You already have authorized access</b> to BD Bank Jobs AI. You do not need to request access.")
        return

    prompt = (
        "🔒 <b>Request Access to BD Bank Jobs AI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Choose the type of access you are requesting:\n\n"
        "• <b>🤖 Bot Usage Permission:</b> Direct access to query the bot in 1-on-1 private chat.\n"
        "• <b>👥 Private Group Invite:</b> Join the official Telegram group for automatic 30-min broadcasts.\n\n"
        "<i>Tap below to submit your request to the bot owner:</i>"
    )
    await send_msg(update, context, prompt, reply_markup=get_access_request_keyboard())


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interactive inline keyboard clicks."""
    if not await enforce_private_access(update, context):
        return

    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "menu:noop":
        return

    # ------------------------------------------------------------
    # Access Request & Permission Callbacks
    # ------------------------------------------------------------
    if data.startswith("req_access:"):
        req_type = data.split(":", 1)[1]  # "bot" or "group"
        user = query.from_user
        user_id = str(user.id)
        username = user.username or ""
        full_name = user.full_name or "Unknown User"

        db.record_access_request(user_id, username, full_name, request_type=req_type)

        if req_type == "bot":
            user_confirm = (
                "📨 <b>Bot Usage Permission Requested</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Your request for <b>Direct Bot Usage Permission</b> has been forwarded to the administrator.\n\n"
                "⏳ <i>You will receive a notification as soon as you are approved. Once approved, you can use all commands (/latest, /fetchall, /categories, /search) directly here!</i>"
            )
            admin_req_type = "🤖 <b>Bot Usage Only (1-on-1 DM, no group join needed)</b>"
            admin_btn_text = "✅ Approve Bot Access"
        else:
            user_confirm = (
                "📨 <b>Private Group Invite Requested</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Your request to join the <b>Private Telegram Group</b> has been submitted to the administrator.\n\n"
                "⏳ <i>You will receive a one-time verified invite link directly from this bot once approved.</i>"
            )
            admin_req_type = "👥 <b>Private Telegram Group Membership</b>"
            admin_btn_text = "✅ Send Group Invite"

        try:
            await query.edit_message_text(user_confirm, parse_mode=ParseMode.HTML)
        except Exception:
            await query.message.reply_text(user_confirm, parse_mode=ParseMode.HTML)

        # Notify administrator in the designated group
        admin_kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(admin_btn_text, callback_data=f"adm_app:{req_type}:{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"adm_rej:{user_id}"),
            ]
        ])
        admin_alert = (
            f"🔔 <b>New Access Request</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User:</b> {html.escape(full_name)} (@{username or 'no_username'})\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"🎯 <b>Requested:</b> {admin_req_type}\n\n"
            f"<i>Admins: Tap below to approve or reject:</i>"
        )
        try:
            await context.bot.send_message(
                chat_id=int(TELEGRAM_CHAT_ID),
                text=admin_alert,
                parse_mode=ParseMode.HTML,
                reply_markup=admin_kb,
            )
        except Exception as e:
            logger.error(f"Failed to forward access request to admin chat {TELEGRAM_CHAT_ID}: {e}")
        return

    # ------------------------------------------------------------
    # Admin Approval / Rejection Callbacks
    # ------------------------------------------------------------
    if data.startswith("adm_app:"):
        parts = data.split(":")
        req_type = parts[1]
        target_uid = parts[2]
        admin_user = query.from_user
        admin_uid = str(admin_user.id)

        if not await can_manage_owner_commands(admin_uid, context):
            await query.answer("⛔ Access Denied: Only the bot owner or delegated managers can approve access requests.", show_alert=True)
            return

        db.authorize_user(target_uid, access_type=req_type, approved_by=admin_uid)

        # Update command visibility scope for the approved user immediately (removes /requestaccess, adds member queries)
        try:
            await context.bot.set_my_commands(
                get_member_commands(),
                scope=BotCommandScopeChat(chat_id=int(target_uid)),
            )
        except Exception as scope_err:
            logger.warning(f"Failed to update scoped commands for user {target_uid}: {scope_err}")
        admin_tag = f"@{admin_user.username}" if admin_user.username else admin_user.first_name

        if req_type == "bot":
            admin_summary = f"✅ <b>Approved for Bot Usage:</b> User <code>{target_uid}</code> by {admin_tag}."
            user_msg = (
                "🎉 <b>Bot Usage Permission Approved!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "The administrator has granted you permission to use the BD Bank Jobs AI Bot!\n\n"
                "You can now query circulars, run searches, and browse categories directly in this chat.\n\n"
                "👇 <i>Get started below:</i>"
            )
            try:
                await context.bot.send_message(
                    chat_id=int(target_uid),
                    text=user_msg,
                    parse_mode=ParseMode.HTML,
                    reply_markup=get_category_keyboard(),
                )
            except Exception as e:
                logger.warning(f"Could not deliver approval DM to user {target_uid}: {e}")
        else:
            invite_link = None
            try:
                invite = await context.bot.create_chat_invite_link(
                    chat_id=int(TELEGRAM_CHAT_ID),
                    member_limit=1,
                    name=f"Invite for {target_uid}",
                )
                invite_link = invite.invite_link
            except Exception as e:
                logger.error(f"Could not generate chat invite link: {e}")

            admin_summary = (
                f"✅ <b>Group Invite Sent:</b> User <code>{target_uid}</code> by {admin_tag}\n"
                f"🔗 Link: {invite_link or 'Error generating link'}"
            )
            user_msg = (
                "🎉 <b>Group Membership Approved!</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "The administrator has approved your invitation to the private <b>BD Bank Jobs AI</b> group!\n\n"
                f"🔗 <b>Your Exclusive Single-Use Invite Link:</b>\n"
                f"{invite_link or 'Please contact admin for link'}\n\n"
                "<i>Welcome! Continuous 30-minute circular broadcasts are active in the group.</i>"
            )
            try:
                await context.bot.send_message(
                    chat_id=int(target_uid),
                    text=user_msg,
                    parse_mode=ParseMode.HTML,
                )
            except Exception as e:
                logger.warning(f"Could not deliver group invite DM to user {target_uid}: {e}")

        try:
            await query.edit_message_text(admin_summary, parse_mode=ParseMode.HTML)
        except Exception:
            await query.message.reply_text(admin_summary, parse_mode=ParseMode.HTML)
        return

    if data.startswith("adm_rej:"):
        target_uid = data.split(":", 1)[1]
        admin_user = query.from_user
        admin_uid = str(admin_user.id)

        if not await can_manage_owner_commands(admin_uid, context):
            await query.answer("⛔ Access Denied: Only the bot owner or delegated managers can reject access requests.", show_alert=True)
            return

        db.reject_user(target_uid, rejected_by=admin_uid)
        admin_tag = f"@{admin_user.username}" if admin_user.username else admin_user.first_name
        admin_summary = f"❌ <b>Rejected:</b> User <code>{target_uid}</code> by {admin_tag}."

        try:
            await query.edit_message_text(admin_summary, parse_mode=ParseMode.HTML)
        except Exception:
            await query.message.reply_text(admin_summary, parse_mode=ParseMode.HTML)

        try:
            await context.bot.send_message(
                chat_id=int(target_uid),
                text=(
                    "ℹ️ <b>Access Request Update</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Your access request was reviewed by the administrator and could not be approved at this time."
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        return

    # ------------------------------------------------------------
    # Admin Mode Toggle Callbacks
    # ------------------------------------------------------------
    if data.startswith("set_mode:"):
        new_mode = data.split(":", 1)[1]
        admin_uid = str(query.from_user.id)
        if not await can_manage_owner_commands(admin_uid, context):
            await query.answer("⛔ Access Denied: Only the bot owner or delegated managers can change bot access mode.", show_alert=True)
            return

        db.set_access_mode(new_mode)
        sync_website_data(f"chore(mode): set 1-on-1 bot access mode to {new_mode}")

        await query.answer(f"✅ 1-on-1 Bot Mode set to {new_mode.upper()}!", show_alert=True)

        mode_text = "🔒 <b>PRIVATE</b> (Admin Approval Required for 1-on-1 DM)" if new_mode == "private" else "🌐 <b>PUBLIC</b> (Open to Everyone for 1-on-1 DM)"
        kb = [
            [
                InlineKeyboardButton("🌐 Set 1-on-1 Bot: PUBLIC", callback_data="set_mode:public"),
                InlineKeyboardButton("🔒 Set 1-on-1 Bot: PRIVATE", callback_data="set_mode:private"),
            ]
        ]
        msg = (
            "⚙️ <b>1-on-1 Bot Access Mode Updated!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Current Active Mode:</b> {mode_text}\n"
            "• <b>Private Group:</b> Strictly Private & Admin-Gated\n"
            f"• <b>Website Status:</b> Synchronized with <code>data/jobs.json</code>\n"
            f"• <b>Updated by:</b> @{query.from_user.username or query.from_user.first_name}\n\n"
            "<i>Tap below anytime to toggle mode:</i>"
        )
        try:
            await query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        except Exception:
            await query.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
        return

    # ------------------------------------------------------------
    # Permission Delegation Callbacks (Primary Owner Only)
    # ------------------------------------------------------------
    if data.startswith("perm_grant:"):
        target_uid = data.split(":", 1)[1]
        owner_user = query.from_user
        owner_uid = str(owner_user.id)

        if not await is_primary_owner(owner_uid, context):
            await query.answer("⛔ Access Denied: Only primary bot owner can grant permissions.", show_alert=True)
            return

        db.grant_owner_permission(target_uid, granted_by=owner_uid)

        try:
            await context.bot.set_my_commands(
                get_delegated_owner_commands(),
                scope=BotCommandScopeChat(chat_id=int(target_uid))
            )
        except Exception as e:
            logger.warning(f"Could not update scoped commands for user {target_uid}: {e}")

        try:
            await context.bot.send_message(
                chat_id=int(target_uid),
                text=(
                    "🎉 <b>Owner Command Permissions Granted!</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "The bot owner has granted you permission to view and execute owner commands:\n"
                    "• <code>/mode</code> — Toggle 1-on-1 Bot Public / Private & sync website\n"
                    "• <code>/requests</code> — Review and approve user access requests\n\n"
                    "Your Telegram command menu has been updated with these commands!"
                ),
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

        await query.answer(f"✅ Granted owner permissions to User {target_uid}!", show_alert=True)

        delegated = db.list_delegated_owners()
        approved = db.list_authorized_users(status="approved")
        text = (
            "👑 <b>Owner Command Permissions Management</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "As the primary bot owner, you can grant or revoke permission for trusted users "
            "to see and execute owner-level commands (<code>/mode</code> and <code>/requests</code>).\n\n"
            "<b>👥 Currently Delegated Users:</b>\n"
        )
        if delegated:
            for u in delegated:
                uname = f"@{u['username']}" if u.get("username") else "no_username"
                fname = u.get("full_name") or "User"
                uid = u["user_id"]
                text += f"• 👤 <b>{html.escape(fname)}</b> ({uname}) — ID: <code>{uid}</code>\n"
        else:
            text += "• <i>No delegated users currently. Only you (Primary Owner) have access to owner commands.</i>\n"

        text += (
            "\n<b>⚙️ Delegation Commands:</b>\n"
            "• <code>/grant &lt;user_id&gt;</code> — Grant owner commands (/mode, /requests) to user\n"
            "• <code>/revoke &lt;user_id&gt;</code> — Revoke owner commands from user\n\n"
            "<i>Or tap an action button below:</i>"
        )
        kb = []
        for u in delegated:
            uname = u.get("username") or u.get("full_name") or u["user_id"]
            kb.append([InlineKeyboardButton(f"❌ Revoke: {uname} ({u['user_id']})", callback_data=f"perm_rev:{u['user_id']}")])
        delegated_ids = {str(u["user_id"]) for u in delegated}
        non_delegated = [u for u in approved if str(u["user_id"]) not in delegated_ids and str(u["user_id"]) != str(TELEGRAM_OWNER_ID)]
        for u in non_delegated[:6]:
            uname = u.get("username") or u.get("full_name") or u["user_id"]
            kb.append([InlineKeyboardButton(f"➕ Grant: {uname} ({u['user_id']})", callback_data=f"perm_grant:{u['user_id']}")])

        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb) if kb else None)
        except Exception:
            pass
        return

    if data.startswith("perm_rev:"):
        target_uid = data.split(":", 1)[1]
        owner_user = query.from_user
        owner_uid = str(owner_user.id)

        if not await is_primary_owner(owner_uid, context):
            await query.answer("⛔ Access Denied: Only primary bot owner can revoke permissions.", show_alert=True)
            return

        db.revoke_owner_permission(target_uid)

        try:
            await context.bot.set_my_commands(
                get_member_commands(),
                scope=BotCommandScopeChat(chat_id=int(target_uid))
            )
        except Exception as e:
            logger.warning(f"Could not revert scoped commands for user {target_uid}: {e}")

        try:
            await context.bot.send_message(
                chat_id=int(target_uid),
                text="ℹ️ <b>Permission Update:</b> Your owner command permissions (<code>/mode</code>, <code>/requests</code>) have been revoked by the bot owner.",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

        await query.answer(f"✅ Revoked owner permissions from User {target_uid}!", show_alert=True)

        delegated = db.list_delegated_owners()
        approved = db.list_authorized_users(status="approved")
        text = (
            "👑 <b>Owner Command Permissions Management</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "As the primary bot owner, you can grant or revoke permission for trusted users "
            "to see and execute owner-level commands (<code>/mode</code> and <code>/requests</code>).\n\n"
            "<b>👥 Currently Delegated Users:</b>\n"
        )
        if delegated:
            for u in delegated:
                uname = f"@{u['username']}" if u.get("username") else "no_username"
                fname = u.get("full_name") or "User"
                uid = u["user_id"]
                text += f"• 👤 <b>{html.escape(fname)}</b> ({uname}) — ID: <code>{uid}</code>\n"
        else:
            text += "• <i>No delegated users currently. Only you (Primary Owner) have access to owner commands.</i>\n"

        text += (
            "\n<b>⚙️ Delegation Commands:</b>\n"
            "• <code>/grant &lt;user_id&gt;</code> — Grant owner commands (/mode, /requests) to user\n"
            "• <code>/revoke &lt;user_id&gt;</code> — Revoke owner commands from user\n\n"
            "<i>Or tap an action button below:</i>"
        )
        kb = []
        for u in delegated:
            uname = u.get("username") or u.get("full_name") or u["user_id"]
            kb.append([InlineKeyboardButton(f"❌ Revoke: {uname} ({u['user_id']})", callback_data=f"perm_rev:{u['user_id']}")])
        delegated_ids = {str(u["user_id"]) for u in delegated}
        non_delegated = [u for u in approved if str(u["user_id"]) not in delegated_ids and str(u["user_id"]) != str(TELEGRAM_OWNER_ID)]
        for u in non_delegated[:6]:
            uname = u.get("username") or u.get("full_name") or u["user_id"]
            kb.append([InlineKeyboardButton(f"➕ Grant: {uname} ({u['user_id']})", callback_data=f"perm_grant:{u['user_id']}")])

        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb) if kb else None)
        except Exception:
            pass
        return

    if data == "menu:fetchall":
        await fetchall_command(update, context)
        return

    if data == "menu:categories":
        text = (
            "📂 <b>Bank Job Categories & Disciplines</b>\n"
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
                InlineKeyboardButton("📚 Fetch All Circulars", callback_data="menu:fetchall"),
            ]
        ])
        await query.message.reply_text("👉 <i>Explore more circulars:</i>", reply_markup=nav_kb)
        return

    if data.startswith("qsearch:"):
        term = data.split(":", 1)[1]
        await execute_search(update, context, term)
        return


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Intelligent natural text query handler:
    When user types plain text (e.g. 'engineer', 'sonali bank', 'audit', 'officer'),
    automatically performs a search!
    """
    if not await enforce_private_access(update, context):
        return
    text = (update.message.text or "").strip()
    if not text or text.startswith("/"):
        return

    logger.info(f"Natural text query received: '{text}'")
    await execute_search(update, context, text)


# ================================================================
# AUTONOMOUS 30-MINUTE BACKGROUND MONITORING ENGINE
# ================================================================

async def periodic_monitoring_task(app: Application):
    """
    Continuous 30-minute automated monitoring engine.
    Scrapes Bangladesh Bank BSCS + all 105+ banks & NBFIs every 30 minutes.
    Automatically purges expired jobs, deduplicates, runs AI analysis,
    and broadcasts newly discovered circulars to Telegram!
    """
    logger.info("30-minute background monitoring task started.")
    while True:
        try:
            logger.info("[AUTO-MONITOR] Starting scheduled 30-minute scan across ALL 105+ institutions...")
            # 1. Clean expired and duplicates
            db.cleanup_expired_jobs()
            db.cleanup_duplicates()

            # 2. Scrape Bangladesh Bank BSCS e-Recruitment
            bb_scraper = BBErecruitmentScraper()
            bb_jobs = await asyncio.to_thread(bb_scraper.scrape_jobs)
            new_count = 0
            for j in bb_jobs:
                if db.insert_job(j) is not None:
                    new_count += 1

            # 3. Scrape ALL 105+ Banks & NBFIs concurrently
            career_scraper = CareerPageScraper()
            sources = [b for b in BANKS if b.get("short_name") != "BB_BSCS" and b.get("enabled", True)]
            bank_jobs = await asyncio.to_thread(career_scraper.scrape_all_concurrent, sources, 15)
            for j in bank_jobs:
                if db.insert_job(j) is not None:
                    new_count += 1

            # 3b. Scrape ALL 5 Modern Job Portals & Aggregators (Bdjobs, LinkedIn, BDJobsToday, Chakrir Khobor, Skill Jobs)
            logger.info("[AUTO-MONITOR] Scraping 5 major portals & circular aggregators...")
            bdjobs_scraper = BdjobsScraper()
            portal_scraper = PortalScraper()
            portal_jobs = await asyncio.to_thread(lambda: bdjobs_scraper.scrape_all_categories() + portal_scraper.scrape_all_portals())
            for j in portal_jobs:
                if db.insert_job(j) is not None:
                    new_count += 1

            # 4. Immediate post-scrape purge of any expired or duplicate jobs
            db.cleanup_expired_jobs()
            db.cleanup_duplicates()

            # Sync static web data for GitHub Pages
            try:
                from export_web_data import export_all
                export_all()
            except Exception as ex:
                logger.warning(f"Failed to export web data: {ex}")

            logger.info(f"[AUTO-MONITOR] Scan completed: {new_count} new circulars inserted across 105+ banks & 5 major portals.")

            # 4. AI Analysis on newly discovered jobs
            unanalyzed = db.get_unanalyzed_jobs()
            if unanalyzed:
                analyzer = JobAnalyzer()
                results = await asyncio.to_thread(analyzer.analyze_batch, unanalyzed)
                for j, analysis in results:
                    if analysis:
                        db.update_job_ai_analysis(j["id"], analysis)

            # 5. Broadcast new jobs to Telegram chat
            unnotified = db.get_unnotified_jobs(min_relevance_score=0.4)
            if unnotified:
                logger.info(f"[AUTO-MONITOR] Broadcasting {len(unnotified)} new circulars to Telegram...")
                chat_id = TELEGRAM_CHAT_ID
                for j in unnotified:
                    card = telegram_notifier.format_job_message(j)
                    if chat_id:
                        for attempt in range(3):
                            try:
                                await app.bot.send_message(
                                    chat_id=chat_id,
                                    text=card,
                                    parse_mode=ParseMode.HTML,
                                    disable_web_page_preview=False,
                                )
                                db.mark_as_notified(j["id"])
                                break
                            except Exception as em:
                                if "Flood control" in str(em) or "RetryAfter" in str(em):
                                    wait_s = 25
                                    if hasattr(em, "retry_after"):
                                        wait_s = int(em.retry_after) + 2
                                    logger.warning(f"Telegram rate limited: pausing {wait_s}s...")
                                    await asyncio.sleep(wait_s)
                                else:
                                    logger.warning(f"Broadcast error for job {j['id']}: {em}")
                                    db.mark_as_notified(j["id"])
                                    break
                        await asyncio.sleep(1.2)

        except Exception as e:
            logger.error(f"[AUTO-MONITOR] Error during periodic scan: {e}", exc_info=True)

        logger.info("[AUTO-MONITOR] Next automated scan in 30 minutes (1800s)...")
        await asyncio.sleep(1800)  # Exactly 30 minutes


async def setup_bot_commands(application: Application):
    """Register menu commands with Telegram API using role-based visibility scopes."""
    try:
        # 1. Default Scope (Guests / Non-approved users): ONLY see /start, /requestaccess, /help
        await application.bot.set_my_commands(get_guest_commands(), scope=BotCommandScopeDefault())

        # 2. Group Chats Scope (All group members): see member commands (NO /mode, /requests, /permissions, /requestaccess)
        await application.bot.set_my_commands(get_member_commands(), scope=BotCommandScopeAllGroupChats())

        # 3. Primary Owner Private Chat Scope: sees ALL commands including /permissions, /mode, /requests
        owner_id = int(str(TELEGRAM_OWNER_ID).strip())
        await application.bot.set_my_commands(get_primary_owner_commands(), scope=BotCommandScopeChat(chat_id=owner_id))

        # 4. Delegated Owners: see /mode and /requests along with member commands (NO /permissions)
        delegated_users = db.list_delegated_owners()
        delegated_ids = set()
        for du in delegated_users:
            uid = du.get("user_id")
            if uid and str(uid).strip() != str(owner_id).strip():
                try:
                    delegated_ids.add(str(uid).strip())
                    await application.bot.set_my_commands(
                        get_delegated_owner_commands(),
                        scope=BotCommandScopeChat(chat_id=int(uid))
                    )
                except Exception:
                    pass

        # 5. Approved 1-on-1 Members (Non-delegated): set member commands in their DM (NO /mode, /requests, /permissions, /requestaccess)
        approved_users = db.list_authorized_users(status="approved")
        for u in approved_users:
            uid = u.get("user_id")
            if uid and str(uid).strip() != str(owner_id).strip() and str(uid).strip() not in delegated_ids:
                try:
                    await application.bot.set_my_commands(get_member_commands(), scope=BotCommandScopeChat(chat_id=int(uid)))
                except Exception:
                    pass

        logger.info("Configured role-based command visibility scopes in Telegram.")
    except Exception as e:
        logger.warning(f"Failed to set scoped bot commands: {e}")


async def post_init(application: Application):
    """Post initialization: set commands and launch 30-minute background monitor."""
    await setup_bot_commands(application)
    asyncio.create_task(periodic_monitoring_task(application))


def main():
    """Start interactive Telegram bot server with 30-minute background monitoring."""
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
        .post_init(post_init)
        .build()
    )

    # Deduplicated, intuitive command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("fetchall", fetchall_command))
    app.add_handler(CommandHandler("fetch_all", fetchall_command))
    app.add_handler(CommandHandler("resend_all", fetchall_command))
    app.add_handler(CommandHandler("all", fetchall_command))
    app.add_handler(CommandHandler("latest", latest_command))
    app.add_handler(CommandHandler("categories", categories_command))
    app.add_handler(CommandHandler("category", categories_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("check", scan_command))
    app.add_handler(CommandHandler("banks", banks_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("mode", mode_command))
    app.add_handler(CommandHandler("toggleprivacy", mode_command))
    app.add_handler(CommandHandler("requests", requests_command))
    app.add_handler(CommandHandler("permissions", permissions_command))
    app.add_handler(CommandHandler("permission", permissions_command))
    app.add_handler(CommandHandler("grant", grant_command))
    app.add_handler(CommandHandler("revoke", revoke_command))
    app.add_handler(CommandHandler("requestaccess", request_access_command))
    app.add_handler(CommandHandler("access", request_access_command))

    # Interactive callback query handler (inline buttons click)
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Natural text message handler (search any keyword without typing slashes)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Auto-leave unauthorized groups (security safeguard)
    app.add_handler(ChatMemberHandler(on_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))

    print("✅ Bot is online with dynamic Public/Private toggle & 30-min auto-monitor across ALL 105+ banks!")
    app.run_polling(poll_interval=0.5, timeout=10, drop_pending_updates=True)


if __name__ == "__main__":
    main()
