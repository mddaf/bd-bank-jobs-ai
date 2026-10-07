"""
Bangladesh Bank Job Monitor — Configuration
============================================
Central configuration for all settings, bank URLs, and scraping rules.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================
# Paths
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)
DB_PATH = STORAGE_DIR / "jobs.db"

# ============================================================
# API Keys
# ============================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_OWNER_ID = os.getenv("TELEGRAM_OWNER_ID", "7938327860")
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")

# ============================================================
# Scraping Settings
# ============================================================
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "30"))
REQUEST_TIMEOUT = 30  # seconds
MIN_DELAY_BETWEEN_REQUESTS = 2  # seconds
MAX_DELAY_BETWEEN_REQUESTS = 5  # seconds
MAX_RETRIES = 3

# Rotate User-Agent to reduce blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

# ============================================================
# Gemini AI Settings
# ============================================================
GEMINI_MODEL = "gemini-3.7-flash"  # Fast & free on student plan
GEMINI_FALLBACK_MODELS = ["gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.8-flash"]
GEMINI_RATE_LIMIT_PER_MINUTE = 15  # Stay well under free tier limits

# ============================================================
# Logging
# ============================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
