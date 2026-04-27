import os
import time
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, send_file
from threading import Thread

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# =====================
# CONFIG
# =====================
TOKEN = "PUT_YOUR_TOKEN"
CHANNEL = "@AndriaGold"

CACHE_TIME = 60
cache = {"data": None, "time": 0}

last_sent = None

# =====================
# GET RAW HTML ONCE
# =====================
def fetch_html():
    url = "https://edahabapp.com/"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=10)
    return res.text

# =====================
# PARSE SNAPSHOT
# =====================
def parse_data(html):
    soup = BeautifulSoup(html, "html.parser")

    prices = {}
    items = soup.find_all("div", class_="price-item")

    gram_24 = None
    ounce_usd = None

    for item in items:
        title = item.find("span", class_="font-medium")
        numbers = item.find_all("span", class_="number-font")

        if not title or len(numbers) == 0:
            continue

        name = title.text.strip()

        # ===== GOLD PRICES =====
        if "عيار" in name:
            if len(numbers) >= 2:
                buy = float(numbers[0].text.replace(",", "").strip())
                sell = float(numbers[1].text.replace(",", "").strip())

                prices[name] = {
                    "بيع": sell,
                    "شراء": buy
                }

                if "24" in name:
                    gram_24 = sell  # ثابت

        # ===== OUNCE =====
        if "أوقية" in name:
            try:
                ounce_usd = float(numbers[0].text.replace(",", "").strip())
                prices["الأوقية العالمية"] = ounce_usd
            except:
                pass

    return prices, gram_24, ounce_usd

# =====================
# MAIN DATA FUNCTION (STABLE SNAPSHOT)
# =====================
def get_all_prices():
    global cache

    if time.time() - cache["time"] < CACHE_TIME:
        return cache["data"]

    html = fetch_html()
    prices, gram_24, ounce_usd = parse_data(html)

    # =====================
    # DOLLAR SAGHA (FIXED FORMULA)
    # =====================
    if gram_24 and ounce_usd:
        dollar_sagha = (gram_24 * 31.103) / ounce_usd
        prices["دولار الصاغة"] = round(dollar_sagha, 2)

    cache = {"data": prices, "time": time.time()}
    return prices

# =====================
# TELEGRAM MESSAGE
# =====================
def format_message(data):
    global last_sent

    msg = "💎 <b>تحديث أسعار الذهب</b>\n\n"
    msg += "📊 <b>الأسعار</b>\n"
    msg += "━━━━━━━━━━━━━━\n"

    trend = ""

    if last_sent and "دولار الصاغة" in data and "دولار الصاغة" in last_sent:
        diff = data["دولار الصاغة"] - last_sent["دولار الصاغة"]

        if diff > 0:
            trend = f"\n📈 ارتفع +{round(diff,2)}"
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
