import os
import time
import requests
from bs4 import BeautifulSoup
from decimal import Decimal, getcontext
from flask import Flask, jsonify
from threading import Thread

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

cache = {"data": None, "time": 0}
CACHE_TIME = 60

last_sent_value = None

# =====================
# DECIMAL CLEAN
# =====================
def D(x):
    return Decimal(x.replace(",", "").strip())

# =====================
# SCRAPE ENGINE
# =====================
def get_snapshot():
    html = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}).text
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
            buy = D(nums[0].text)
            sell = D(nums[1].text)

            data[name] = {
                "buy": float(buy),
                "sell": float(sell)
            }

            if "24" in name:
                gram_24 = sell

        if "أوقية" in name:
            ounce = D(nums[0].text)

    # =====================
    # DOLLAR SAGHA
    # =====================
    dollar = None

    if gram_24 and ounce:
        raw = (gram_24 * Decimal("31.103")) / ounce
        dollar = raw.quantize(Decimal("0.01"))
        data["دولار الصاغة"] = float(dollar)

    return data, dollar

# =====================
# TELEGRAM SEND
# =====================
def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHANNEL,
        "text": msg,
        "parse_mode": "HTML"
    })

# =====================
# FORMAT MESSAGE
# =====================
def format_msg(data):
    msg = "💎 <b>تحديث أسعار الذهب</b>\n\n"
    msg += "━━━━━━━━━━━━━━\n"

    for k, v in data.items():
        if isinstance(v, dict):
            msg += f"🔸 {k}\n"
            msg += f"بيع: {v['sell']} | شراء: {v['buy']}\n"
            msg += "──────────────\n"
        else:
            msg += f"📌 {k}: {v}\n"

    msg += "━━━━━━━━━━━━━━\n⚡ Railway Stable Engine"

    return msg

# =====================
# LOOP (THREAD SAFE)
# =====================
def loop():
    global last_sent_value

    while True:
        try:
            data, dollar = get_snapshot()

            if dollar is not None:

                if last_sent_value is not None:
                    diff = abs(dollar - last_sent_value)

                    if diff > Decimal("0.01"):
                        print("⚠️ Difference:", diff)

                if dollar != last_sent_value:
                    send(format_msg(data))
                    last_sent_value = dollar

        except Exception as e:
            print("Error:", e)

        time.sleep(60)

# =====================
# API ROUTE
# =====================
@app.route("/")
def home():
    return "Bot is running ✅"

@app.route("/api")
def api():
    data, _ = get_snapshot()
    return jsonify(data)

# =====================
# START THREAD + FLASK
# =====================
if __name__ == "__main__":
    Thread(target=loop, daemon=True).start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
