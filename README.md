# 🏦 BD Bank Jobs AI (`bd-bank-jobs-ai`)

<div align="center">

[![Live Website](https://img.shields.io/badge/🌐_Live_Website-bd--bank--jobs--ai-10b981?style=for-the-badge&logo=githubpages&logoColor=white)](https://mddaf.github.io/bd-bank-jobs-ai/)
[![Telegram Bot](https://img.shields.io/badge/💬_Telegram_Bot-BDBankJobMonitorBot-229ED9?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/BDBankJobMonitorBot)
[![Monitored Institutions](https://img.shields.io/badge/🏦_Institutions-105+_Monitored-6366f1?style=for-the-badge)](https://mddaf.github.io/bd-bank-jobs-ai/#directory-section)
[![Continuous Monitoring](https://img.shields.io/badge/⏱️_Scan_Interval-Every_30_Minutes-f59e0b?style=for-the-badge)](#-autonomous-30-minute-engine)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

**Real-Time Autonomous AI Job Intelligence Agent for Bangladesh's Banking & Financial Sector.**  
*Continuous 30-minute concurrent monitoring across 105+ financial institutions, zero-duplicate cadre protection, automated expired deadline purges, interactive Telegram alerts with instant chat recovery, and a modern glassmorphic web dashboard.*

[**Explore Live Dashboard ➔**](https://mddaf.github.io/bd-bank-jobs-ai/) • [**Join Telegram Alerts ➔**](https://t.me/BDBankJobMonitorBot)

</div>

---

## 🌟 Overview

The banking and financial sector in Bangladesh publishes recruitment circulars across fragmented channels: the Bangladesh Bank Bankers' Selection Committee Secretariat (BSCS), direct institutional portals, third-party boards, and corporate career pages. 

**BD Bank Jobs AI** is a production-ready, autonomous pair-monitoring agent that:
1. **Scrapes 105+ financial institutions** simultaneously using high-speed concurrent threading in under 15 seconds.
2. **Eliminates noise & past ads:** Parses every date format (Bengali numerals, ISO, ordinals) and permanently blacklists expired circulars.
3. **Preserves engineering cadres & disciplines:** Employs deterministic fingerprinting and token-overlap fuzzy matching while guaranteeing that distinct disciplines (Civil, Mechanical, Electrical, Textile, Architecture, Leather, IT, Law, Audit) are never falsely collapsed.
4. **Delivers minimalistic Telegram alert cards:** Native `<blockquote>` cards featuring calculated days remaining (*"11 days left"*, *"Ends Today!"*), direct PDF circular links, and 1-click apply links.
5. **Restores chat history with `/fetchall`:** Lost or cleared your Telegram chat? Send `/fetchall` anytime to instantly restore every verified active circular.
6. **Hosts an interactive web application on GitHub Pages:** Fully static, responsive, glassmorphic UI with real-time search, category filters, and an interactive 105+ institutions directory.

---

## 🌐 Live Website & Web Application

The interactive web dashboard is hosted live on GitHub Pages:
👉 **[https://mddaf.github.io/bd-bank-jobs-ai/](https://mddaf.github.io/bd-bank-jobs-ai/)**

### Web Dashboard Highlights:
- **Telegram Card Aesthetics:** Displays vacancies, salary scale, education eligibility, and verified match score.
- **Dynamic Urgency Chips:** Visual countdown indicators:
  - 🔴 *Ends Today!* / *X Days Left* (≤ 2 days)
  - 🟡 *X Days Left* (3–7 days)
  - 🟢 *X Days Left* (> 7 days)
- **Instant Search & Discipline Chips:** Filter circulars live by keyword or tap chips: `⚙️ Engineering`, `💻 IT & Systems`, `⚖️ Law & Legal`, `📈 Financial Analyst`, `📊 Audit & Accounts`, `👔 Officers & Cadre`.
- **105+ Institutions Directory:** Searchable bank directory categorized into SOCBs, Private, Islamic, Foreign, Digital, and NBFIs with direct career portal links.
- **Dark & Light Mode:** Glassmorphism UI with smooth toggle and persistent `localStorage` preference.
- **Automated Sync:** Updated static data (`data/jobs.json`) exported on every 30-minute scan cycle.

---

## 🏦 Comprehensive Coverage (105+ Institutions)

Every 30-minute cycle monitors **105+ registered institutions** across Bangladesh:

| Sector Category | Count | Notable Institutions Monitored |
| :--- | :---: | :--- |
| **🏛️ Central Recruitment** | 2 | **Bangladesh Bank BSCS Central Recruitment**, Bangladesh Bank Main Portal |
| **🏢 State-Owned Commercial Banks (SOCBs)** | 6 | Sonali Bank PLC, Janata Bank PLC, Agrani Bank PLC, Rupali Bank PLC, BASIC Bank PLC, BDBL |
| **🌾 Specialized Development Banks (SDBs)** | 3 | Bangladesh Krishi Bank (BKB), Rajshahi Krishi Unnayan Bank (RAKUB), Probashi Kollyan Bank (PKB) |
| **💼 Private Commercial Banks (Conventional)** | 33 | BRAC Bank, The City Bank, Dutch-Bangla Bank (DBBL), Eastern Bank (EBL), Mutual Trust Bank (MTB), Prime Bank, Bank Asia, Dhaka Bank, IFIC Bank, Jamuna Bank, NCC Bank, Pubali Bank, Trust Bank, UCB, Uttara Bank, etc. |
| **🕌 Islamic Shariah Banks** | 10 | Islami Bank Bangladesh PLC (IBBL), Al-Arafah, Social Islami (SIBL), First Security Islami, Shahjalal Islami (SJIBL), EXIM Bank, Union Bank, Global Islami, Standard Bank, ICB Islamic |
| **🌍 Foreign Commercial Banks** | 9 | Standard Chartered Bangladesh, HSBC Bangladesh, Commercial Bank of Ceylon, Woori Bank, State Bank of India, Habib Bank, Bank Alfalah, Citibank N.A., National Bank of Pakistan |
| **📱 Digital Banks** | 2 | Nagad Digital Bank PLC, Kori Digital Bank PLC |
| **🤝 Non-Scheduled Banks** | 5 | Ansar-VDP Unnayan Bank, Karmasangsthan Bank, Grameen Bank, Jubilee Bank, Palli Sanchay Bank |
| **📈 NBFIs (Non-Bank Financial Institutions)** | 35 | IDLC Finance PLC, IPDC Finance, LankaBangla Finance, DBH Finance, United Finance, IDCOL, BIFC, CVC Finance, Fareast Finance, FAS Finance, First Finance, GSP, Hajj Finance, IIDFC, ILFSL, Meridian, MIDAS, National Housing, Phoenix, Premier Leasing, Prime Finance, SABINCO, SFIL, UBICO, Union Capital, Uttara Finance, etc. |

---

## 🤖 Interactive Telegram Bot Server

The bot server (`bot_server.py`) operates 24/7 with a clean, deduplicated, and intuitive command menu:

```
───────────────────────────────────────────────────────────
💬 Bot Commands Guide:
───────────────────────────────────────────────────────────
• /fetchall      — Deliver ALL circulars from database (instant chat recovery!)
• /latest        — Show 5 most recent verified banking circulars
• /categories    — One-tap discipline browser with live counts (Engineering, IT, Law, etc.)
• /search <word> — Instant keyword search or quick-search chips
• /scan          — Trigger on-demand live scrape across 105+ institutions with progress updates
• /banks         — View complete directory of 105+ monitored institutions
• /stats         — View database and monitoring metrics
• /help          — Command guide & instructions
───────────────────────────────────────────────────────────
```

### 📱 Sample Minimalistic Telegram Alert Card:

```html
<blockquote>
🏛️ BANGLADESH BANK / BSCS
State-Owned & Central Bank Recruitment
───────────────────────────
💼 Assistant Engineer (Civil) / Senior Officer (Grade-9)

👥 Vacancies: 8
💰 Salary: National Pay Scale Grade-9
🎓 Req: B.Sc in Civil Engineering from recognized university
📅 Deadline: 18 Oct 2026 (11 days left)
🎯 Match: 95% Verified
</blockquote>

📄 Official vacancy for Civil Engineers across participating state-owned banks.
🇧🇩 সমন্বিত রাষ্ট্রায়ত্ত ব্যাংকে সহকারী প্রকৌশলী (সিভিল) নিয়োগ বিজ্ঞপ্তি।
───────────────────────────
📄 Official Circular (PDF)   •   👉 Apply Online ➔
```

---

## 🛡️ Core Intelligence & Safeguards

### 1. Smart Expired Deadline Purge
- **Pre-Insert Quarantine:** [`utils/date_parser.py`](utils/date_parser.py) parses English and Bengali dates, detecting whether a deadline has passed. Circulars with expired dates or obsolete upload timestamps (e.g. 2019–2025 ads sitting on old career pages) are automatically blacklisted into `expired_jobs` and never entered into the database.
- **Active Job Cleanup:** [`Database.cleanup_expired_jobs()`](storage/database.py) runs on startup, on every 30-minute scan, and before any user command to ensure zero expired postings are ever displayed.

### 2. Cadre-Safe Deduplication
- [`utils/deduplicator.py`](utils/deduplicator.py) generates normalized SHA-256 fingerprints to merge duplicate postings from multiple sources (e.g. BB BSCS vs individual bank career page), keeping the official PDF circular link.
- **Cadre Protection:** Explicitly isolates engineering disciplines (Civil, Mechanical, Electrical, Textile, Architecture, Leather) and professional cadres (IT, Law, Audit, Analyst) so they are **never merged as duplicates**.

---

## 🚀 Quick Start & Installation

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/mddaf/bd-bank-jobs-ai.git
cd bd-bank-jobs-ai

python -m venv venv
venv\Scripts\activate          # Windows PowerShell / CMD
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Fill in your configuration:
```ini
# Google Gemini API Key (Optional AI summaries, fallback heuristic active)
GEMINI_API_KEY=your_gemini_api_key_here

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN=8463455416:AAE0TRPwAxJeLGcLC5au2yzzYNz6CrqM9rI
TELEGRAM_CHAT_ID=-5486651424
```

### 3. Launch the Autonomous System

#### Option A: 24/7 Telegram Bot & 30-Minute Monitoring Daemon (Recommended)
```bash
python bot_server.py
```
*Starts the interactive Telegram bot server, registers command handlers, serves `/fetchall`, and runs the 30-minute background scraping engine continuously.*

#### Option B: Fresh Database Wipe & Telegram Broadcast
```bash
python fresh_start_broadcast.py
```
*Clears the SQLite database, performs a clean concurrent scrape across all 105+ institutions, analyzes jobs, and broadcasts active circulars directly to your Telegram chat.*

#### Option C: Sync Static Data for GitHub Pages
```bash
python export_web_data.py
```
*Generates updated `data/jobs.json` for the GitHub Pages static web app.*

#### Option D: Run Local Web Server
```bash
python -m http.server 8000
```
*Preview the web app locally at `http://localhost:8000`.*

---

## 📁 Repository Structure

```
bd-bank-jobs-ai/
├── config/
│   ├── settings.py                # Environment paths and Telegram credentials
│   └── banks.py                   # Registry of 105+ banks, NBFIs & portals
├── scrapers/
│   ├── base_scraper.py            # Base scraper with fast HTTP session & headers
│   ├── bb_erecruitment_scraper.py # Bangladesh Bank BSCS e-Recruitment scraper
│   └── career_page_scraper.py     # Concurrent scraper with strict exclusion rules
├── storage/
│   └── database.py                # SQLite layer with WAL mode, deduplication & expiry purge
├── utils/
│   ├── date_parser.py             # Bengali/English deadline parser & expiry detector
│   └── deduplicator.py            # Deterministic fingerprinting with cadre safety
├── ai/
│   ├── gemini_client.py           # Gemini 3.7/3.5 Flash client with rate limit handling
│   └── job_analyzer.py            # AI categorization & smart bilingual heuristic fallback
├── notifiers/
│   └── telegram_bot.py            # Modern minimalistic blockquote Telegram card formatter
├── bot_server.py                  # 24/7 interactive Telegram bot & 30-min monitoring engine
├── fresh_start_broadcast.py       # Fresh database reset, scrape & Telegram broadcast script
├── export_web_data.py             # Exporter generating static JSON for GitHub Pages
├── index.html                     # Semantic, accessible web dashboard for GitHub Pages
├── css/
│   └── style.css                  # Responsive Vanilla CSS with glassmorphic design system
├── js/
│   └── app.js                     # Modular Vanilla JS for search, filters, directory & modal
├── data/
│   └── jobs.json                  # Static dataset snapshot of active circulars & institutions
├── .github/workflows/
│   ├── job_monitor.yml            # Automated 30-minute GitHub Actions workflow
│   └── deploy_pages.yml           # GitHub Pages deployment workflow
├── .nojekyll                      # Disables Jekyll processing on GitHub Pages
├── requirements.txt               # Python dependencies
└── README.md                      # Project documentation
```

---

## ⚡ GitHub Actions Automation

This repository includes two automated workflows in `.github/workflows/`:
1. **`job_monitor.yml`**: Scheduled every 30 minutes from 6 AM to 11 PM BST (UTC+6) to scan, ingest, and deliver alerts completely free in the cloud.
2. **`deploy_pages.yml`**: Automatically publishes frontend updates to GitHub Pages on every push to `master`.

---

## 📄 License

Distributed under the **MIT License**. Free for educational, personal, and open-source use.

---

<div align="center">

**Built with precision for Bangladesh financial sector job seekers.**  
*Continuous 30-minute monitoring • Zero duplicates • Zero expired circulars*

[**Visit Live Website**](https://mddaf.github.io/bd-bank-jobs-ai/) • [**Open Telegram Bot**](https://t.me/BDBankJobMonitorBot)

</div>
