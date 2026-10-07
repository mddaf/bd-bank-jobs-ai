"""
Email Notifier
================
Sends job notification emails via Gmail SMTP.
Sends daily digest emails with all new bank job postings.

Setup:
  1. Enable 2-Factor Auth on your Gmail account
  2. Generate an App Password: Google Account → Security → App Passwords
  3. Set EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER in .env
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config.settings import EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Sends job notification emails via Gmail SMTP."""

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587

    def __init__(self, sender: str = None, password: str = None, receiver: str = None):
        self.sender = sender or EMAIL_SENDER
        self.password = password or EMAIL_PASSWORD
        self.receiver = receiver or EMAIL_RECEIVER

    @property
    def is_configured(self) -> bool:
        """Check if email credentials are set."""
        if not self.sender or not self.password or not self.receiver:
            return False
        if "your_" in str(self.sender).lower() or "example.com" in str(self.sender).lower():
            return False
        return True

    def send_daily_digest(self, jobs: list) -> bool:
        """
        Send a daily digest email with all new job postings.

        Args:
            jobs: List of job dicts

        Returns:
            True if email sent successfully
        """
        if not self.is_configured:
            logger.warning("Email not configured, skipping.")
            return False

        if not jobs:
            logger.info("No jobs to email.")
            return True

        subject = f"🏦 Bank Job Alert — {len(jobs)} New Positions ({datetime.now().strftime('%d %b %Y')})"
        html_body = self._build_digest_html(jobs)

        return self._send_email(subject, html_body)

    def _build_digest_html(self, jobs: list) -> str:
        """Build a beautiful HTML email for the daily digest."""
        job_rows = ""
        for i, job in enumerate(jobs, 1):
            score = job.get("ai_relevance_score", 0)
            score_color = "#22c55e" if score >= 0.7 else "#f59e0b" if score >= 0.4 else "#ef4444"

            job_rows += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 16px; vertical-align: top;">
                    <div style="font-weight: 600; font-size: 16px; color: #1f2937; margin-bottom: 4px;">
                        {i}. {job.get('title', 'Unknown Position')}
                    </div>
                    <div style="color: #6b7280; font-size: 14px; margin-bottom: 8px;">
                        🏢 {job.get('organization', 'Unknown')}
                        {f' | 📅 Deadline: {job.get("deadline")}' if job.get("deadline") else ''}
                    </div>
                    <div style="color: #374151; font-size: 14px; margin-bottom: 8px;">
                        {job.get('ai_summary', '') or ''}
                    </div>
                    <div style="display: flex; gap: 12px; align-items: center;">
                        <span style="background: {score_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">
                            {score:.0%} match
                        </span>
                        <a href="{job.get('url', '#')}" style="color: #2563eb; text-decoration: none; font-size: 14px;">
                            Apply →
                        </a>
                    </div>
                </td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; background: #f3f4f6; margin: 0; padding: 20px;">
            <div style="max-width: 640px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">

                <!-- Header -->
                <div style="background: linear-gradient(135deg, #1e3a5f, #2563eb); padding: 32px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">🏦 Bank Job Alert</h1>
                    <p style="color: #93c5fd; margin: 8px 0 0; font-size: 14px;">
                        {len(jobs)} new positions found — {datetime.now().strftime('%d %B %Y')}
                    </p>
                </div>

                <!-- Job List -->
                <table style="width: 100%; border-collapse: collapse;">
                    {job_rows}
                </table>

                <!-- Footer -->
                <div style="padding: 24px; text-align: center; background: #f9fafb; border-top: 1px solid #e5e7eb;">
                    <p style="color: #9ca3af; font-size: 12px; margin: 0;">
                        🤖 Powered by BD Bank Job Monitor<br>
                        You're receiving this because you subscribed to bank job alerts.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _send_email(self, subject: str, html_body: str) -> bool:
        """Send an HTML email via Gmail SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.sender
            msg["To"] = self.receiver
            msg["Subject"] = subject

            # Attach HTML body
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            # Connect and send
            with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.sender, self.password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {self.receiver}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "Email authentication failed! Make sure you're using an "
                "App Password (not your regular Gmail password). "
                "Go to: Google Account → Security → App Passwords"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
