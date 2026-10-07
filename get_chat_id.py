"""
Telegram Chat ID Auto-Configurator
====================================
Waits for you to send a message to your Telegram bot,
automatically extracts your Chat ID, updates .env,
and sends a test alert message.
"""

import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

if not BOT_TOKEN or "your_telegram" in BOT_TOKEN:
    print("❌ Error: TELEGRAM_BOT_TOKEN is not configured in .env!")
    sys.exit(1)

# Check bot info
me_resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe").json()
if not me_resp.get("ok"):
    print(f"❌ Invalid Bot Token: {me_resp.get('description')}")
    sys.exit(1)

bot_username = me_resp["result"]["username"]
print("=" * 60)
print(f"🤖 Connected to Bot: @{bot_username} ({me_resp['result']['first_name']})")
print("=" * 60)
print(f"\n👉 Please open Telegram, search @{bot_username}")
print("   and send any message (e.g. /start or 'hi') to your bot.\n")
print("Waiting for message (timeout: 60s)...", flush=True)

start_time = time.time()
chat_id = None
sender_name = None

while time.time() - start_time < 60:
    try:
        updates = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates").json()
        if updates.get("ok") and updates.get("result"):
            last_update = updates["result"][-1]
            message = last_update.get("message") or last_update.get("channel_post")
            if message and "chat" in message:
                chat_id = str(message["chat"]["id"])
                sender_name = message["chat"].get("first_name", "User")
                break
    except Exception as e:
        print(f"Checking error: {e}")
    time.sleep(2)

if not chat_id:
    print("\n⏰ Timed out waiting for message.")
    print(f"Make sure you searched @{bot_username} on Telegram and pressed START.")
    sys.exit(1)

print(f"\n✅ Message received from {sender_name}!")
print(f"📋 Your Chat ID is: {chat_id}")

# Update .env file
env_path = Path(".env")
if env_path.exists():
    content = env_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    new_lines = []
    updated = False
    for line in lines:
        if line.startswith("TELEGRAM_CHAT_ID="):
            new_lines.append(f"TELEGRAM_CHAT_ID={chat_id}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"TELEGRAM_CHAT_ID={chat_id}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print("💾 Saved TELEGRAM_CHAT_ID directly to .env!")

# Send test confirmation message to user
welcome_text = (
    "🎉 *Bank Job Monitor — Connected!*\n\n"
    f"Hello {sender_name}! Your Telegram alerts are now configured and ready.\n\n"
    "Whenever a new bank or financial institution job is posted in Bangladesh, "
    "you will receive instant alerts right here!\n\n"
    "🏦 *Monitored Sources:*\n"
    "• Bangladesh Bank & 20+ Commercial Banks\n"
    "• NBFIs & Financial Institutions\n"
    "• bdjobs.com Banking Section\n\n"
    "🤖 _Powered by Gemini AI_"
)

send_resp = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    json={"chat_id": chat_id, "text": welcome_text, "parse_mode": "Markdown"},
).json()

if send_resp.get("ok"):
    print("🚀 Sent welcome message to your Telegram!")
else:
    # Try plain text fallback
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": "Bank Job Monitor connected successfully!"},
    )
    print("🚀 Sent plain text confirmation to your Telegram!")

print("\n🎉 SETUP COMPLETE! You are ready to run: python main.py")
