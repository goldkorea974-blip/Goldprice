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
            market_dollar = None

            for item in items:
                title = item.find("span", class_="font-medium")
                nums = item.find_all("span", class_="number-font")

                if not title or len(nums) == 0:
                    continue

                name = title.text.strip()

                # =====================
                # الذهب
                # =====================
                if "عيار" in name and len(nums) >= 2:
                    sell = D(nums[0].text)
                    buy = D(nums[1].text)

                    data[name] = {
                        "buy": str(buy),
                        "sell": str(sell)
                    }

                    if "24" in name:
                        gram_24 = sell

                # =====================
                # الأوقية
                # =====================
                if "أوقية" in name or "اونصة" in name or "ounce" in name.lower():
                    ounce = D(nums[0].text)
                    data["الأوقية العالمية"] = str(ounce)

                # =====================
                # الدولار الأمريكي (من الموقع)
                # =====================
                if "الدولار الأمريكي" in name or "USD" in name:
                    market_dollar = D(nums[0].text)
                    data["الدولار الأمريكي"] = str(market_dollar)

            # =====================
            # دولار الصاغة
            # =====================
            gold_dollar = None
            if gram_24 and ounce:
                gold_dollar = (gram_24 * Decimal("31.1034768")) / ounce
                data["دولار الصاغة"] = f"{gold_dollar:.2f}"

            # =====================
            # HASH للتغيير
            # =====================
            page_hash = hashlib.md5(str(data).encode()).hexdigest()

            return data, market_dollar, gold_dollar, page_hash

        except Exception as e:
            log(f"Error: {e}")
            time.sleep(2)

    return {}, None, None, None

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
    msg = "💎 <b>تحديث لحظي للذهب</b>\n\n"
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
# LOOP (LIVE SYSTEM)
# =====================
def loop():
    global last_hash

    while True:
        try:
            data, market_dollar, gold_dollar, page_hash = get_snapshot()

            if not data:
                continue

            # أول تشغيل
            if last_hash is None:
                send(format_msg(data))
                last_hash = page_hash
                time.sleep(10)
                continue

            # أي تغيير
            if page_hash != last_hash:
                send(format_msg(data))
                last_hash = page_hash

            time.sleep(10)

        except Exception as e:
            log(f"Loop error: {e}")
            time.sleep(5)

# =====================
# API
# =====================
@app.route("/")
def home():
    return "💎 Live Gold System Running"

@app.route("/api")
def api():
    data, _, _, _ = get_snapshot()
    return jsonify(data)

# =====================
# START
# =====================
if __name__ == "__main__":
    Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
