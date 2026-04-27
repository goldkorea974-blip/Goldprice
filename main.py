import os
import time
import requests
from bs4 import BeautifulSoup
from decimal import Decimal, getcontext
from flask import Flask, jsonify, send_file
from threading import Thread

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# =====================
# CONFIG
# =====================
TOKEN = "https://t.me/AndriaGold"
CHANNEL = "@AndriaGold"

CACHE_TIME = 60
cache = {"data": None, "time": 0}

last_sent = None

# 🔥 Precision Engine setup
getcontext().prec = 28

# =====================
# FETCH HTML
# =====================
def fetch_html():
    url = "https://edahabapp.com/"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=10)
    return res.text

# =====================
# CLEAN NUMBER
# =====================
def clean_number(text):
    return Decimal(text.replace(",", "").strip())

# =====================
# PARSE DATA
# =====================
def parse_data(html):
    soup = BeautifulSoup(html, "html.parser")
    items = soup.find_all("div", class_="price-item")

    prices = {}

    gram_24 = None
    ounce_usd = None

    for item in items:
        title = item.find("span", class_="font-medium")
        numbers = item.find_all("span", class_="number-font")

        if not title or len(numbers) == 0:
            continue

        name = title.text.strip()

        # ===== GOLD =====
        if "عيار" in name:
            if len(numbers) >= 2:
                buy = clean_number(numbers[0].text)
                sell = clean_number(numbers[1].text)

                prices[name] = {
                    "بيع": float(sell),
                    "شراء": float(buy)
                }

                if "24" in name:
                    gram_24 = sell

        # ===== OUNCE =====
        if "أوقية" in name:
            ounce_usd = clean_number(numbers[0].text)
            prices["الأوقية العالمية"] = float(ounce_usd)

    return prices, gram_24, ounce_usd

# =====================
# CORE ENGINE
# =====================
def get_all_prices():
    global cache

    if time.time() - cache["time"] < CACHE_TIME:
        return cache["data"]

    html = fetch_html()
    prices, gram_24, ounce_usd = parse_data(html)

    # =====================
    # DOLLAR SAGHA
    # =====================
    if gram_24 and ounce_usd:
        raw = (gram_24 * Decimal("31.103")) / ounce_usd
        prices["دولار الصاغة"] = float(raw.quantize(Decimal("0.01")))

    cache = {"data": prices, "time": time.time()}
    return prices

# =====================
# TELEGRAM FORMAT
# =====================
def format_message(data):
    global last_sent

    msg = "💎 <b>تحديث أسعار الذهب</b>\n\n"
    msg += "📊 الأسعار\n"
    msg += "━━━━━━━━━━━━━━\n"

    trend = ""

    if last_sent and "دولار الصاغة" in data:
        diff = data["دولار الصاغة"] - last_sent.get("دولار الصاغة", 0)

        if diff > 0:
            trend = f"\n📈 زاد +{round(diff,2)}"
        elif diff < 0:
            trend = f"\n📉 نزل {round(diff,2)}"
        else:
            trend = "\n⚖️ ثابت"

    for k, v in data.items():
        if isinstance(v, dict):
            msg += f"🔸 {k}\n"
            msg += f"بيع: {v['بيع']} | شراء: {v['شراء']}\n"
            msg += "──────────────\n"
        else:
            msg += f"📌 {k}: {v}\n"

    msg += "━━━━━━━━━━━━━━"
    msg += trend
    msg += "\n⚡ تحديث تلقائي"

    return msg

# =====================
# SEND TELEGRAM
# =====================
def send_to_channel(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHANNEL,
        "text": message,
        "parse_mode": "HTML"
    })

# =====================
# LOOP
# =====================
def loop():
    global last_sent

    while True:
        data = get_all_prices()

        if data and data != last_sent:
            msg = format_message(data)
            send_to_channel(msg)
            last_sent = data

        time.sleep(60)

# =====================
# API
# =====================
@app.route("/api/prices")
def api():
    return jsonify(get_all_prices())

# =====================
# WEB
# =====================
@app.route("/")
def home():
    return send_file("index.html")

# =====================
# RUN
# =====================
if __name__ == "__main__":
    Thread(target=loop).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
