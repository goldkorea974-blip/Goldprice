import os
import time
import json
import hashlib
import requests
import random
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
TOKEN = "8165343576:AAHjfPZpUUUDvWk3WbC1XocQ_MGQ1aESLT0"
CHANNEL = "@AndriaGold"
URL = "https://edahabapp.com/"
API_KEY = os.getenv("API_KEY")

getcontext().prec = 28

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
    global fail_count

    headers = {
        "User-Agent": "Mozilla/5.0",
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

            page_hash = hashlib.md5(str(data).encode()).hexdigest()

            fail_count = 0
            return data, page_hash

        except Exception as e:
            fail_count += 1
            log(f"Error: {e}")
            time.sleep(3)

    return {}, None

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
# FORMAT
# =====================
def format_msg(data):
    msg = "💎 <b>تحديث لحظي للذهب</b>\n\n━━━━━━━━━━━━━━\n"

    for k, v in data.items():
        if isinstance(v, dict):
            msg += f"🔸 <b>{k}</b>\n🟢 بيع: {v['sell']} | 🔴 شراء: {v['buy']}\n──────────────\n"
        else:
            msg += f"📌 {k}: <b>{v}</b>\n"

    return msg + "━━━━━━━━━━━━━━\n"

# =====================
# LOOP
# =====================
def loop():
    global last_hash, last_data, sent_close_msg, sent_open_msg

    while True:
        try:
            now = datetime.now(egypt_tz)
            hour = now.hour
            log(f"Current hour: {hour}")

            if 10 <= hour < 24:
                sent_close_msg = False

                # 🔥 رسالة فتح السوق (إجبارية)
                if not sent_open_msg:
                    log("Market opened → forcing first send")
                    data, page_hash = get_snapshot()

                    if data:
                        send(format_msg(data))
                        last_hash = page_hash
                        last_data = data
                        sent_open_msg = True
                    else:
                        log("No data yet after open")

                # 📊 التحديث الطبيعي
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
                    msg = "🌙 <b>إغلاق سوق الذهب اليوم</b>\n\n"

                    if last_data:
                        msg += "📊 <b>آخر سعر قبل الإغلاق:</b>\n━━━━━━━━━━━━━━\n"

                        for k, v in last_data.items():
                            if isinstance(v, dict):
                                msg += f"🔸 <b>{k}</b>\n🟢 بيع: {v['sell']} | 🔴 شراء: {v['buy']}\n──────────────\n"
                            else:
                                msg += f"📌 {k}: <b>{v}</b>\n"

                        msg += "━━━━━━━━━━━━━━\n"

                    msg += "\n❤️ شكراً لمتابعتكم\n💎 نلقاكم 10 صباحاً"

                    send(msg)
                    sent_close_msg = True

                # 🔄 إعادة ضبط الفتح لليوم الجديد
                sent_open_msg = False

                time.sleep(60)

        except Exception as e:
            log(f"Loop error: {e}")
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

@app.route("/")
def home():
    return "💎 Live Gold System Running Secure"

# =====================
# START
# =====================
if __name__ == "__main__":
    Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
