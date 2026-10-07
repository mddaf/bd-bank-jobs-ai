"""
Telegram Bot Notifier
=======================
Sends beautifully formatted job alerts to a Telegram channel or chat.
Uses the python-telegram-bot library with async support.

Setup:
  1. Talk to @BotFather on Telegram → /newbot → get BOT_TOKEN
  2. Create a channel/group → add bot as admin
  3. Get CHAT_ID via @userinfobot or from the channel URL
  4. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env
"""

import logging
import asyncio
import html
import re
from datetime import date
from typing import Optional
from telegram import Bot
from telegram.constants import ParseMode
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.date_parser import parse_deadline

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends job notifications via Telegram bot."""

    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID
        self._bot = None

        if not self.bot_token or not self.chat_id:
            logger.warning(
                "Telegram not configured! Set TELEGRAM_BOT_TOKEN and "
                "TELEGRAM_CHAT_ID in your .env file."
            )

    @property
    def is_configured(self) -> bool:
        """Check if Telegram credentials are set."""
        if not self.bot_token or not self.chat_id:
            return False
        if "your_telegram" in str(self.bot_token).lower() or "your_telegram" in str(self.chat_id).lower():
            return False
        return True

    def _get_bot(self) -> Bot:
        """Get or create the Telegram bot instance."""
        if self._bot is None:
            self._bot = Bot(token=self.bot_token)
        return self._bot

    def format_job_message(self, job: dict) -> str:
        """
        Format a job posting into a modern, clean, and minimalistic Telegram card.
        Contains all vital information without clutter.
        """
        title = (job.get("title") or "Banking Opportunity").strip()
        org = (job.get("organization") or "Financial Institution").strip()
        url = (job.get("url") or "").strip()
        desc = (job.get("description") or "").strip()
        source_type = (job.get("source_type") or "").lower()
        score = float(job.get("ai_relevance_score", 0) or 0)

        # 1. Clean Title (remove button tags, extra braces, repetitive bank name)
        clean_title = re.sub(r'\[\s*(?:view|pdf|download)?\s*circular\s*\]', '', title, flags=re.IGNORECASE)
        clean_title = re.sub(r'\[\s*view\s*\]', '', clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r'\s+(?:of|for)\s+[A-Za-z0-9\s\.\(\)\-]+Bank[A-Za-z0-9\s\.\(\)\-]*', '', clean_title, flags=re.IGNORECASE)
        clean_title = re.sub(r'\s{2,}', ' ', clean_title).strip()

        # 2. Sector styling & Subtitle
        org_lower = org.lower()
        if source_type == "state_owned" or any(k in org_lower for k in ["bangladesh bank", "bscs", "sonali", "janata", "agrani", "rupali", "basic", "krishi", "karmasangsthan", "probashi", "ansar"]):
            icon = "🏛️"
            sector_subtitle = "State-Owned Bank • Central Recruitment (BSCS)"
        elif source_type == "islami" or any(k in org_lower for k in ["islami", "al-arafah", "shariah", "sibl", "sjibl"]):
            icon = "🕌"
            sector_subtitle = "Islamic Shariah-Compliant Commercial Bank"
        elif source_type == "nbfi" or any(k in org_lower for k in ["finance", "idlc", "ipdc", "leasing"]):
            icon = "💼"
            sector_subtitle = "Non-Bank Financial Institution (NBFI)"
        else:
            icon = "🏢"
            sector_subtitle = "Private Commercial Bank"

        # 3. Extract Vacancies, Salary, Eligibility
        vacancies = None
        vac_m = re.search(r'Vacanc(?:ies|y):\s*(\d+\s*post[s]?)', desc, re.IGNORECASE)
        if vac_m:
            vacancies = vac_m.group(1).strip()
        elif "post" in desc.lower():
            p_m = re.search(r'(\d+\s*posts?)', desc, re.IGNORECASE)
            if p_m:
                vacancies = p_m.group(1).strip()

        salary = None
        sal_m = re.search(r'Salary\s*Scale:\s*([^|]+)', desc, re.IGNORECASE)
        if sal_m:
            salary = sal_m.group(1).strip()
        elif job.get("estimated_salary_range"):
            salary = str(job.get("estimated_salary_range"))

        eligibility = None
        req_m = re.search(r'Requirements:\s*([^|]+)', desc, re.IGNORECASE)
        if req_m:
            eligibility = req_m.group(1).strip()
        elif job.get("ai_key_requirements"):
            reqs = job.get("ai_key_requirements")
            if isinstance(reqs, list) and reqs:
                eligibility = reqs[0]
            elif isinstance(reqs, str):
                eligibility = reqs

        # 4. Smart Deadline formatting with days remaining
        raw_dl = job.get("deadline")
        parsed_dl = parse_deadline(raw_dl) or parse_deadline(title)
        if parsed_dl:
            days_left = (parsed_dl - date.today()).days
            dl_formatted = parsed_dl.strftime("%d %b %Y")
            if days_left > 1:
                deadline_display = f"{dl_formatted} <i>({days_left} days left)</i>"
            elif days_left == 1:
                deadline_display = f"{dl_formatted} <b>(Tomorrow!)</b>"
            elif days_left == 0:
                deadline_display = f"{dl_formatted} <b>(Ends Today!)</b>"
            else:
                deadline_display = dl_formatted
        elif raw_dl:
            deadline_display = html.escape(str(raw_dl))
        else:
            deadline_display = "Official Circular"

        # 5. Build Structured Blockquote Card
        card_items = []
        if vacancies:
            card_items.append(f"👥 <b>Vacancies:</b> {html.escape(vacancies)}")
        if salary:
            card_items.append(f"💰 <b>Salary:</b> {html.escape(salary[:55])}")
        if eligibility:
            card_items.append(f"🎓 <b>Req:</b> {html.escape(eligibility[:65])}")
        card_items.append(f"📅 <b>Deadline:</b> {deadline_display}")
        card_items.append(f"🎯 <b>Match:</b> {score:.0%} Verified")

        card_block = "<blockquote>\n" + "\n".join(card_items) + "\n</blockquote>"

        # 6. Concise Bilingual Summaries
        summaries = []
        summary_en = (job.get("ai_summary") or "").strip()
        if summary_en and not any(k in summary_en.lower() for k in ["not an employment", "no summary", "not available"]):
            summaries.append(f"📄 {html.escape(summary_en)}")

        summary_bn = (job.get("ai_summary_bn") or "").strip()
        if summary_bn and not any(k in summary_bn for k in ["কোনো চাকরির", "সারাংশ পাওয়া"]):
            summaries.append(f"🇧🇩 {html.escape(summary_bn)}")

        # 7. Action Links (Direct PDF and Apply Portal)
        links = []
        circ_match = re.search(r'Circular\s*PDF:\s*(https?://[^\s|]+)', desc)
        apply_match = re.search(r'Apply\s*Portal:\s*(https?://[^\s|]+)', desc)

        circ_url = circ_match.group(1).strip() if circ_match else None
        apply_url = apply_match.group(1).strip() if apply_match else None

        if not circ_url and (url.endswith(".pdf") or ".pdf#" in url or "erecruitment.bb.org.bd/career" in url):
            circ_url = url

        if circ_url and apply_url:
            links.append(f'📄 <a href="{html.escape(circ_url)}"><b>Official Circular (PDF)</b></a>   •   👉 <a href="{html.escape(apply_url)}"><b>Apply Online ➔</b></a>')
        elif circ_url:
            links.append(f'📄 <a href="{html.escape(circ_url)}"><b>View Official Circular (PDF) ➔</b></a>')
        elif url and url.startswith("http"):
            links.append(f'👉 <a href="{html.escape(url)}"><b>Apply / View Official Circular ➔</b></a>')
        else:
            links.append('ℹ️ <i>Check official bank career portal.</i>')

        # Assemble modern minimalistic message
        parts = [
            f"{icon} <b>{html.escape(org.upper())}</b>",
            f"<i>{sector_subtitle}</i>",
            "───────────────────────────",
            f"💼 <b>{html.escape(clean_title)}</b>",
            "",
            card_block,
        ]

        if summaries:
            parts.append("")
            parts.extend(summaries)

        parts.append("───────────────────────────")
        parts.extend(links)

        return "\n".join(parts)

    def format_daily_digest(self, jobs: list) -> str:
        """Format multiple jobs into a daily digest message."""
        if not jobs:
            return "📊 <b>Daily Bank Job Digest</b>\n\nNo new banking jobs found today."

        lines = [
            "📊 <b>Daily Bank Job Digest</b>",
            f"📈 <b>{len(jobs)}</b> new positions found!\n",
            "━━━━━━━━━━━━━━━━━━━━━━",
        ]

        for i, job in enumerate(jobs[:15], 1):
            title = html.escape(job.get("title", "Unknown"))
            org = html.escape(job.get("organization", "Unknown"))
            url = job.get("url", "")
            score = float(job.get("ai_relevance_score", 0) or 0)

            lines.extend([
                "",
                f"<b>{i}. {title}</b>",
                f"   🏢 {org} | 🎯 {score:.0%} match",
            ])
            if url:
                lines.append(f'   🔗 <a href="{html.escape(url)}">Apply</a>')

        if len(jobs) > 15:
            lines.append(f"\n<i>...and {len(jobs) - 15} more</i>")

        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "🤖 <i>Powered by BD Bank Job Monitor</i>",
        ])

        return "\n".join(lines)

    def send_message(self, text: str) -> bool:
        """Send a message synchronously via Telegram Bot API."""
        if not self.is_configured:
            logger.warning("Telegram not configured, skipping notification.")
            return False
        import requests
        import time
        import re

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, timeout=15)
                data = resp.json()
                if data.get("ok"):
                    return True

                # Rate limit handling (429 Flood Control)
                if data.get("error_code") == 429 or "retry after" in str(data.get("description", "")).lower():
                    retry_sec = data.get("parameters", {}).get("retry_after", 5)
                    logger.warning(f"Telegram rate limit (429). Sleeping {retry_sec} seconds before retry...")
                    time.sleep(retry_sec + 1)
                    continue

                logger.error(f"Telegram API error: {data.get('description')}")
                if "can't parse entities" in str(data.get("description", "")).lower():
                    plain_text = re.sub(r'<[^>]+>', '', text)
                    fb_resp = requests.post(
                        url,
                        json={"chat_id": self.chat_id, "text": plain_text},
                        timeout=15,
                    )
                    return fb_resp.json().get("ok", False)
                return False
            except Exception as e:
                logger.error(f"Failed to send Telegram message: {e}")
                time.sleep(1)
        return False

    def notify_job(self, job: dict) -> bool:
        """Send a notification for a single job."""
        message = self.format_job_message(job)
        success = self.send_message(message)
        if success:
            logger.info(f"Telegram notification sent: {job.get('title', '?')}")
        return success

    def notify_batch(self, jobs: list) -> int:
        """
        Send notifications for multiple jobs.
        Sends individual alerts for high-relevance jobs,
        digest for lower-relevance ones.

        Returns the number of successfully sent notifications.
        """
        if not self.is_configured:
            logger.warning("Telegram not configured.")
            return 0

        sent_count = 0
        high_relevance = [j for j in jobs if j.get("ai_relevance_score", 0) >= 0.6]
        low_relevance = [j for j in jobs if j.get("ai_relevance_score", 0) < 0.6]

        # Send individual alerts for high-relevance jobs
        for job in high_relevance:
            if self.notify_job(job):
                sent_count += 1
            import time
            time.sleep(1)  # Respect Telegram rate limits

        # Send digest for lower-relevance jobs
        if low_relevance:
            digest = self.format_daily_digest(low_relevance)
            if self.send_message(digest):
                sent_count += 1

        logger.info(f"Sent {sent_count} Telegram notifications ({len(high_relevance)} individual + {'1 digest' if low_relevance else '0 digest'})")
        return sent_count

    def send_error_alert(self, error_message: str) -> bool:
        """Send an error alert (when the scraper itself fails)."""
        msg = (
            "⚠️ *Bank Job Monitor — Error Alert*\n\n"
            f"🔴 {self._escape_md(error_message)}\n\n"
            "_The job monitor encountered an error\\. "
            "Please check the logs\\._"
        )
        return self.send_message(msg)

    @staticmethod
    def _escape_md(text: str) -> str:
        """Escape special characters for Telegram MarkdownV2."""
        if not text:
            return ""
        # Characters that need escaping in MarkdownV2
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#',
                         '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
