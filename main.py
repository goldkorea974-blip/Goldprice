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
TOKEN = "8165343576:AAGr_uWTBUMGCgcdahiCicHN3DehLaBOUf0"
CHANNEL = "@AndriaGold"

# =====================
# CACHE
# =====================
cache = {"data": None, "time": 0}
CACHE_TIME = 60

# =====================
# SCRAPING
# =====================
def get_all_prices():
    global cache

    if time.time() - cache["time"] < CACHE_TIME:
        return cache["data"]

    url = "https://edahabapp.com/"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        prices = {}
        items = soup.find_all("div", class_="price-item")

        for item in items:
            title = item.find("span", class_="font-medium")
            numbers = item.find_all("span", class_="number-font")

            if not title or not numbers:
                continue

            name = title.text.strip()

            if "عيار" in name or "ذهب" in name:
                if len(numbers) >= 2:
                    prices[name] = {
                        "بيع": numbers[0].text.strip(),
                        "شراء": numbers[1].text.strip()
                    }
            else:
                prices[name] = numbers[0].text.strip()

        cache = {"data": prices, "time": time.time()}
        return prices

    except Exception as e:
        return {"error": str(e)}

# =====================
# TELEGRAM
# =====================
def send_to_channel(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, data=data)

def send_prices():
    data = get_all_prices()

    msg = "💰 <b>أسعار الذهب الآن</b>\n\n"

    for k, v in data.items():
        if isinstance(v, dict):
            msg += f"🔸 {k}\n"
            msg += f"بيع: {v['بيع']} | شراء: {v['شراء']}\n\n"
        else:
            msg += f"{k}: {v}\n"

    send_to_channel(msg)

# =====================
# LOOP (كل 5 دقائق)
# =====================
def loop():
    while True:
        send_prices()
        time.sleep(300)

# =====================
# API
# =====================
@app.route("/api/prices")
def api():
    return jsonify(get_all_prices())

# =====================
# FRONTEND
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
