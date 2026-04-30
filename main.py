import os
import time
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from decimal import Decimal, getcontext
from flask import Flask, jsonify
from threading import Thread
from datetime import datetime
import pytz

# =====================
# FLASK APP
# =====================
app = Flask(__name__)

# =====================
# CONFIG
# =====================
TOKEN = "8165343576:AAGr_uWTBUMGCgcdahiCicHN3DehLaBOUf0"
CHANNEL = "@AndriaGold"
URL = "https://edahabapp.com/"

getcontext().prec = 28

# =====================
# TIMEZONE
# =====================
egypt_tz = pytz.timezone("Africa/Cairo")

# =====================
# STATE
# =====================
last_hash = None
last_sent_value = None
start_sent = False
end_sent = False

# =====================
# LOG
# =====================
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# =====================
# CLEAN DECIMAL
# =====================
def D(x):
    return Decimal(x.replace(",", "").strip())

# =====================
# SNAPSHOT
# =====================
def get_snapshot(retries=3):
    for attempt in range(retries):
        try:
            log(f"Fetching data attempt {attempt+1}")

            html = requests.get(
                URL,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            ).text

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

                    data[name] = {
                        "buy": str(buy),
                        "sell": str(sell)
                    }

                    if "24" in name:
                        gram_24 = sell

                if "أوقية" in name or "اونصة" in name or "ounce" in name.lower():
                    ounce = D(nums[0].text)
                    data["الأوقية العالمية"] = str(ounce)

            dollar = None
            if gram_24 and ounce:
                dollar = (gram_24 * Decimal("31.1034768")) / ounce
                data["دولار الصاغة"] = f"{dollar:.2f}"

            # =====================
            # HASH (منع التكرار)
            # =====================
            page_hash = hashlib.md5(str(data).encode()).hexdigest()

            log("Snapshot OK")
            return data, dollar, page_hash

        except Exception as e:
            log(f"Snapshot error: {e}")
            time.sleep(2)

    log("Snapshot FAILED ❌")
    return {}, None, None

# =====================
# TELEGRAM SEND
# =====================
def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🌐 الموقع", "url": "https://andriagold.netlify.app/"},
                {"text": "📢 القناة", "url": "https://t.me/AndreaGold"}
            ]
        ]
    }

    requests.post(url, data={
        "chat_id": CHANNEL,
        "text": msg,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(keyboard)
    }, timeout=10)

# =====================
# FORMAT MESSAGE
# =====================
def format_msg(data):
    msg = "💎 <b>تحديث أسعار الذهب</b>\n\n"
    msg += "━━━━━━━━━━━━━━\n"

    for k, v in data.items():
        if isinstance(v, dict):
            msg += f"🔸 <b>{k}</b>\n"
            msg += f"🟢 بيع: {v['sell']} | 🔴 شراء: {v['buy']}\n"
            msg += "──────────────\n"
        else:
            msg += f"📌 {k}: <b>{v}</b>\n"

    msg += "━━━━━━━━━━━━━━\n"
    return msg

# =====================
# LOOP
# =====================
def loop():
    global last_hash, last_sent_value, start_sent, end_sent

    while True:
        try:
            now = datetime.now(egypt_tz)
            hour = now.hour

            log(f"Tick | {hour}")

            if 10 <= hour <= 23:

                data, dollar, page_hash = get_snapshot()

                if data:

                    # 🔥 منع التكرار
                    if page_hash != last_hash:

                        send(format_msg(data))

                        last_hash = page_hash
                        last_sent_value = dollar

                        start_sent = True
                        end_sent = False

            elif hour == 0 and not end_sent:
                data, _, _ = get_snapshot()
                send("📉 نهاية التداول")
                end_sent = True
                start_sent = False

        except Exception as e:
            log(f"Loop error: {e}")

        time.sleep(15)

# =====================
# API
# =====================
@app.route("/")
def home():
    return "💎 Gold Bot Running"

@app.route("/api")
def api():
    data, _, _ = get_snapshot()
    return jsonify(data)

# =====================
# START
# =====================
if __name__ == "__main__":
    Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
