
import os
import time
import json
import hashlib
import requests
import random
import logging
from bs4 import BeautifulSoup
from decimal import Decimal, getcontext
from flask import Flask, jsonify, request
from threading import Thread
from datetime import datetime
import pytz

# =====================
# FLASK APP
# =====================
app = Flask(__name__)

# =====================
# CONFIG (SECURE)
# =====================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8165343576:AAHjfPZpUUUDvWk3WbC1XocQ_MGQ1aESLT0")
CHANNEL = os.getenv("TELEGRAM_CHANNEL", "@AndriaGold")
URL = os.getenv("GOLD_URL", "https://edahabapp.com/")
API_KEY = os.getenv("API_KEY")

getcontext().prec = 28

# =====================
# LOGGING
# =====================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# =====================
# TIMEZONE
# =====================
egypt_tz = pytz.timezone("Africa/Cairo")

# =====================
# STATE
# =====================
last_hash = None
last_data = None
sent_close_msg = False
sent_open_msg = False
fail_count = 0
MAX_FAILS = 5

# =====================
# CLEAN DECIMAL
# =====================
def D(x):
    return Decimal(x.replace(",", "").strip())

# =====================
# SNAPSHOT
# =====================
def get_snapshot(retries=3):
    global fail_count

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for attempt in range(retries):
        try:
            time.sleep(2 + random.randint(0, 3))

            html = requests.get(URL, headers=headers, timeout=10).text
            soup = BeautifulSoup(html, "html.parser")
            items = soup.find_all("div", class_="price-item")

            data = {}
            gram_24 = None
            ounce = None

            for item in items:
                title = item.find("span", class_="font-medium")
                nums = item.find_all("span", class_="number-font")

                if not title or len(nums) == 0:
                    continue

                name = title.text.strip()

                if "عيار" in name and len(nums) >= 2:
                    sell = D(nums[0].text)
                    buy = D(nums[1].text)
                    data[name] = {"buy": str(buy), "sell": str(sell)}

                    if "24" in name:
                        gram_24 = sell

                if "أوقية" in name or "ounce" in name.lower():
                    ounce = D(nums[0].text)
                    data["الأوقية العالمية"] = str(ounce)

                if "USD" in name or "الدولار" in name:
                    data["الدولار الأمريكي"] = str(D(nums[0].text))

            if gram_24 and ounce:
                gold_dollar = (gram_24 * Decimal("31.1034768")) / ounce
                data["دولار الصاغة"] = f"{gold_dollar:.2f}"

            if not data:
                log.warning("No data extracted from page")
                time.sleep(3)
                continue

            # Sort keys for consistent hash
            sorted_data = dict(sorted(data.items()))
            page_hash = hashlib.md5(str(sorted_data).encode()).hexdigest()

            fail_count = 0
            return data, page_hash

        except Exception as e:
            fail_count += 1
            log.error(f"Attempt {attempt + 1}/{retries} failed: {e}")
            time.sleep(3)

    log.error("All snapshot attempts failed")
    return {}, None

# =====================
# TELEGRAM SEND
# =====================
def send(msg, retries=3):
    if not TOKEN:
        log.error("TELEGRAM_BOT_TOKEN not set")
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🌐 الموقع", "url": "https://andriagold.netlify.app/"},
                {"text": "📢 القناة", "url": "https://t.me/AndreaGold"}
            ]
        ]
    }

    for attempt in range(retries):
        try:
            resp = requests.post(url, data={
                "chat_id": CHANNEL,
                "text": msg,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(keyboard)
            }, timeout=10)

            if resp.status_code == 200:
                log.info("Message sent successfully")
                return True
            else:
                log.warning(f"Telegram API returned {resp.status_code}: {resp.text}")
                time.sleep(2)

        except Exception as e:
            log.error(f"Send attempt {attempt + 1}/{retries} failed: {e}")
            time.sleep(2)

    log.error("Failed to send message after all retries")
    return False

# =====================
# FORMAT
# =====================
def format_msg(data):
    msg = "💎 <b>تحديث لحظي للذهب</b>\\n\\n━━━━━━━━━━━━━━\\n"

    for k, v in data.items():
        if isinstance(v, dict):
            msg += f"🔸 <b>{k}</b>\\n🟢 بيع: {v['sell']} | 🔴 شراء: {v['buy']}\\n──────────────\\n"
        else:
            msg += f"📌 {k}: <b>{v}</b>\\n"

    return msg + "━━━━━━━━━━━━━━\\n"

# =====================
# LOOP
# =====================
def loop():
    global last_hash, last_data, sent_close_msg, sent_open_msg

    while True:
        try:
            now = datetime.now(egypt_tz)
            hour = now.hour
            log.info(f"Current hour: {hour}")

            if 10 <= hour < 24:
                sent_close_msg = False

                if not sent_open_msg:
                    log.info("Market opened → forcing first send")
                    data, page_hash = get_snapshot()

                    if data:
                        send(format_msg(data))
                        last_hash = page_hash
                        last_data = data
                        sent_open_msg = True
                    else:
                        log.warning("No data yet after open")
                        time.sleep(30)
                        continue

                data, page_hash = get_snapshot()

                if not data:
                    time.sleep(10)
                    continue

                if last_hash is None:
                    send(format_msg(data))
                    last_hash = page_hash
                    last_data = data
                    time.sleep(10)
                    continue

                if page_hash != last_hash:
                    send(format_msg(data))
                    last_hash = page_hash
                    last_data = data

                time.sleep(10)

            else:
                if not sent_close_msg:
                    msg = "🌙 <b>إغلاق سوق الذهب اليوم</b>\\n\\n"

                    if last_data:
                        msg += "📊 <b>آخر سعر قبل الإغلاق:</b>\\n━━━━━━━━━━━━━━\\n"

                        for k, v in last_data.items():
                            if isinstance(v, dict):
                                msg += f"🔸 <b>{k}</b>\\n🟢 بيع: {v['sell']} | 🔴 شراء: {v['buy']}\\n──────────────\\n"
                            else:
                                msg += f"📌 {k}: <b>{v}</b>\\n"

                        msg += "━━━━━━━━━━━━━━\\n"

                    msg += "\\n❤️ شكراً لمتابعتكم\\n💎 نلقاكم 10 صباحاً"

                    send(msg)
                    sent_close_msg = True

                sent_open_msg = False
                time.sleep(60)

        except Exception as e:
            log.error(f"Loop error: {e}")
            time.sleep(5)

# =====================
# API (SECURE)
# =====================
@app.route("/api")
def api():
    key = request.args.get("key")

    if key != API_KEY:
        return jsonify({"error": "unauthorized"}), 403

    data, _ = get_snapshot()
    return jsonify(data)

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "last_data": bool(last_data),
        "fail_count": fail_count,
        "sent_open": sent_open_msg,
        "sent_close": sent_close_msg
    })

@app.route("/")
def home():
    return "💎 Live Gold System Running Secure"

# =====================
# START
# =====================
if __name__ == "__main__":
    Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
'''

with open('/mnt/agents/output/gold_bot_improved.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("File saved successfully!")
