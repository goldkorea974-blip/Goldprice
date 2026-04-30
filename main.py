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
last_sent_time = 0

# =====================
# LOG
# =====================
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# =====================
# CLEAN NUMBER
# =====================
def D(x):
    return Decimal(x.replace(",", "").strip())

# =====================
# SNAPSHOT
# =====================
def get_snapshot(retries=3):
    for _ in range(retries):
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
            usd = None

            for item in items:
                title = item.find("span", class_="font-medium")
                nums = item.find_all("span", class_="number-font")

                if not title or len(nums) == 0:
                    continue

                name = title.text.strip()

                # ================= GOLD =================
                if "عيار" in name and len(nums) >= 2:
                    sell = D(nums[0].text)
                    buy = D(nums[1].text)

                    data[name] = {
                        "buy": float(buy),
                        "sell": float(sell)
                    }

                    if "24" in name:
                        gram_24 = sell

                # ================= OUNCE =================
                if "أوقية" in name or "ounce" in name.lower():
                    ounce = D(nums[0].text)
                    data["الأوقية العالمية"] = float(ounce)

                # ================= USD =================
                if "الدولار" in name:
                    usd = D(nums[0].text)
                    data["الدولار الأمريكي"] = float(usd)

            # ================= GOLD DOLLAR =================
            if gram_24 and ounce:
                gold_usd = (gram_24 * Decimal("31.1034768")) / ounce
                data["دولار الصاغة"] = float(round(gold_usd, 2))

            return data

        except Exception as e:
            log(f"Error: {e}")
            time.sleep(2)

    return {}

# =====================
# SMART CORRECTION ENGINE
# =====================
karat_map = {
    "24": 24,
    "21": 21,
    "18": 18,
    "14": 14
}

def correct_prices(data):
    corrected = data.copy()

    gold_items = {k: v for k, v in data.items() if "عيار" in k}

    for k in gold_items:
        try:
            current = gold_items[k]["sell"]
            k_num = karat_map[k.split()[1]]

            estimates = []

            for k2 in gold_items:
                if k2 == k:
                    continue

                k2_num = karat_map[k2.split()[1]]
                est = gold_items[k2]["sell"] * (k_num / k2_num)
                estimates.append(est)

            if not estimates:
                continue

            estimated = sum(estimates) / len(estimates)

            # سماحية الخطأ
            if abs(current - estimated) > 10:
                corrected[k]["sell"] = round(float(estimated), 2)
                corrected[k]["buy"] = round(float(estimated - 40), 2)

        except:
            continue

    return corrected

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
# LOOP
# =====================
def loop():
    global last_hash, last_sent_time

    while True:
        try:
            data = get_snapshot()
            if not data:
                continue

            # تصحيح الأسعار
            data = correct_prices(data)

            page_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
            now = time.time()

            if last_hash is None:
                send(format_msg(data))
                last_hash = page_hash
                last_sent_time = now
                time.sleep(10)
                continue

            if page_hash != last_hash and (now - last_sent_time) > 5:
                send(format_msg(data))
                last_hash = page_hash
                last_sent_time = now

            time.sleep(10)

        except Exception as e:
            log(f"Loop error: {e}")
            time.sleep(5)

# =====================
# API
# =====================
@app.route("/")
def home():
    return "💎 Smart Gold System Running"

@app.route("/api")
def api():
    return jsonify(get_snapshot())

# =====================
# START
# =====================
if __name__ == "__main__":
    Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
