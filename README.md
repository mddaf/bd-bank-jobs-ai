# 🏦 BD Bank Job Monitor

**AI-powered agent that monitors job postings from all banks and financial institutions in Bangladesh and sends instant Telegram/Email notifications.**

## Features

- 🔍 **Scrapes 25+ banks** — State-owned, private, NBFIs, and financial institutions
- 🌐 **Monitors job portals** — bdjobs.com with banking category filters
- 🤖 **Gemini AI Analysis** — Bilingual summaries (English + Bangla), relevance scoring
- 📱 **Telegram Alerts** — Instant push notifications with beautiful formatting
- 📧 **Email Digests** — Daily summary emails with HTML design
- ⏰ **Automated** — Runs every 30 minutes via GitHub Actions (free!)
- 🔄 **Deduplication** — Never sends duplicate alerts
- 💰 **100% Free** — Uses only free-tier services

## Quick Start

### 1. Clone & Setup
```bash
git clone <your-repo-url>
cd "AI Agent"
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configure API Keys
Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

| Key | How to Get |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) (free with student plan) |
| `TELEGRAM_BOT_TOKEN` | Talk to [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` |
| `TELEGRAM_CHAT_ID` | Automatically configured via `python get_chat_id.py`! |

#### Easy Telegram Setup (1 Step):
Once you put your `TELEGRAM_BOT_TOKEN` in `.env`, just run:
```bash
python get_chat_id.py
```
Send any message to your bot on Telegram, and it will automatically detect your Chat ID, update your `.env`, and send a test confirmation alert!

### 3. Run
```bash
# Full pipeline (scrape → analyze → notify)
python main.py

# Individual steps
python main.py --scrape     # Only scrape
python main.py --analyze    # Only run AI analysis
python main.py --notify     # Only send notifications
python main.py --stats      # View statistics
python main.py --bot        # Run interactive Telegram bot server

### 4. Interactive Telegram Commands
When the bot is running (`python main.py --bot`), you can chat directly with [@BJMAI_bot](https://t.me/BJMAI_bot) or in your group using:

| Command | Action |
|---|---|
| `/latest` | Shows the 5 most recent bank job postings with apply links |
| `/search <keyword>` | Search jobs by role or bank (e.g. `/search IT` or `/search Officer`) |
| `/stats` | View database count and scraping monitor stats |
| `/check` | Triggers an immediate live scrape across all banks |
| `/help` | Displays the help menu and command list |

### 5. Automate with GitHub Actions
1. Push this repo to GitHub
2. Go to **Settings → Secrets → Actions** and add:
   - `GEMINI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. The workflow runs automatically every 30 minutes!

## Project Structure

```
AI Agent/
├── config/
│   ├── settings.py          # Configuration & env vars
│   └── banks.py             # Bank registry (25+ institutions)
├── scrapers/
│   ├── base_scraper.py      # Abstract scraper with retry/rate-limiting
│   ├── career_page_scraper.py # Direct bank career pages
│   └── bdjobs_scraper.py    # bdjobs.com scraper
├── ai/
│   ├── gemini_client.py     # Gemini API wrapper
│   └── job_analyzer.py      # AI job analysis & scoring
├── storage/
│   └── database.py          # SQLite database layer
├── notifiers/
│   ├── telegram_bot.py      # Telegram notifications
│   └── email_notifier.py    # Email digest
├── main.py                  # Entry point
├── .github/workflows/
│   └── job_monitor.yml      # GitHub Actions automation
└── requirements.txt
```

## Monitored Institutions

### Banks (20+)
Bangladesh Bank, Sonali Bank, Janata Bank, Agrani Bank, Rupali Bank, BASIC Bank, DBBL, BRAC Bank, EBL, City Bank, Islami Bank, Prime Bank, Pubali Bank, MTB, Bank Asia, Mercantile Bank, Standard Bank, Southeast Bank, NCC Bank, ONE Bank, UCBL, National Bank, Dhaka Bank

### Financial Institutions
IDCOL, ICB, Lanka Bangla Finance, IPDC Finance

### Job Portals
bdjobs.com (Banking category), chakri.com

## License

MIT
