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
from typing import Optional
from telegram import Bot
from telegram.constants import ParseMode
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

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
        Format a job posting into a beautiful Telegram HTML message.
        """
        title = html.escape(job.get("title", "Unknown Position"))
        org = html.escape(job.get("organization", "Unknown"))
        category = html.escape(str(job.get("ai_category", "Banking")))
        exp = html.escape(str(job.get("ai_experience_level", "Any")))
        url = job.get("url", "")

        lines = [
            "🏦 <b>New Bank Job Alert!</b>\n",
            f"📌 <b>{title}</b>",
            f"🏢 <b>Organization:</b> {org}",
            f"📋 <b>Category:</b> {category} ({exp} level)",
        ]

        summary = job.get("ai_summary")
        if summary:
            lines.extend(["", "📝 <b>Summary:</b>", html.escape(summary)])

        summary_bn = job.get("ai_summary_bn")
        if summary_bn:
            lines.extend(["", "📝 <b>সারাংশ:</b>", html.escape(summary_bn)])

        deadline = job.get("deadline")
        if deadline:
            lines.append(f"\n📅 <b>Deadline:</b> {html.escape(deadline)}")

        score = float(job.get("ai_relevance_score", 0) or 0)
        stars = "⭐" * min(5, max(1, round(score * 5)))
        lines.append(f"🎯 <b>Relevance:</b> {stars} ({score:.0%})")

        if url:
            lines.append(f'\n🔗 <a href="{html.escape(url)}"><b>Apply / View Details →</b></a>')

        org_tag = "".join(ch for ch in org if ch.isalnum())[:20]
        lines.extend(["", f"#BankJob #Bangladesh #{org_tag}"])

        return "\n".join(lines)

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
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        try:
            resp = requests.post(url, json=payload, timeout=15)
            data = resp.json()
            if data.get("ok"):
                return True
            else:
                logger.error(f"Telegram API error: {data.get('description')}")
                import re
                plain_text = re.sub(r'<[^>]+>', '', text)
                fallback_payload = {
                    "chat_id": self.chat_id,
                    "text": plain_text,
                }
                fb_resp = requests.post(url, json=fallback_payload, timeout=15)
                return fb_resp.json().get("ok", False)
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
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
