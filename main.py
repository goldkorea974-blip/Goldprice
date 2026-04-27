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

cache = {"data": None, "time": 0}
CACHE_TIME = 60

last_sent = None

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

        gram_24 = None
        ounce_usd = None

        for item in items:
            title = item.find("span", class_="font-medium")
            numbers = item.find_all("span", class_="number-font")

            if not title or not numbers:
                continue

            name = title.text.strip()

            # ===== أسعار الذهب =====
            if "عيار" in name:
                if len(numbers) >= 2:
                    buy = float(numbers[0].text.replace(",", ""))
                    sell = float(numbers[1].text.replace(",", ""))

                    prices[name] = {"بيع": buy, "شراء": buy}

                    if "24" in name:
                        gram_24 = sell

            # ===== الأوقية =====
            if "أوقية" in name:
                try:
                    ounce_usd = float(numbers[0].text.replace(",", ""))
                    prices["الأوقية العالمية"] = ounce_usd
                except:
                    pass

        # =====================
        # دولار الصاغة
        # =====================
        dollar_sagha = None
        if gram_24 and ounce_usd:
            dollar_sagha = (gram_24 * 31.103) / ounce_usd
            prices["دولار الصاغة"] = round(dollar_sagha, 2)

        cache = {"data": prices, "time": time.time()}
        return prices

    except Exception as e:
        return {"error": str(e)}

# =====================
# TELEGRAM MESSAGE (TABLE)
# =====================
def format_message(data):
    msg = "💎 <b>تحديث أسعار الذهب</b>\n\n"

    msg += "📊 <b>جدول الأسعار</b>\n"
    msg += "━━━━━━━━━━━━━━\n"

    for k, v in data.items():
        if isinstance(v, dict):
            msg += f"🔸 {k}\n"
            msg += f"بيع: {v['بيع']} | شراء: {v['شراء']}\n"
            msg += "──────────────\n"
        else:
            msg += f"📌 {k}: {v}\n"

    msg += "━━━━━━━━━━━━━━\n"
    msg += "⚡ تم التحديث تلقائيًا"

    return msg

# =====================
# TELEGRAM SEND
# =====================
def send_to_channel(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHANNEL,
        "text": message,
        "parse_mode": "HTML"
    })

# =====================
# AUTO LOOP
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
# WEB PAGE (TABLE VIEW)
# =====================
@app.route("/")
def home():
    data = get_all_prices()

    html = """
    <html>
    <head>
        <title>Gold Prices</title>
        <style>
            body { font-family: Arial; background:#111; color:#fff; text-align:center; }
            table { margin:auto; border-collapse: collapse; width:80%; }
            th, td { border:1px solid #444; padding:10px; }
            th { background:#222; }
            tr:nth-child(even){background:#1a1a1a;}
        </style>
    </head>
    <body>
        <h2>💎 أسعار الذهب</h2>
        <table>
            <tr><th>النوع</th><th>القيمة</th></tr>
    """

    for k, v in data.items():
        if isinstance(v, dict):
            html += f"<tr><td>{k}</td><td>بيع: {v['بيع']} | شراء: {v['شراء']}</td></tr>"
        else:
            html += f"<tr><td>{k}</td><td>{v}</td></tr>"

    html += """
        </table>
    </body>
    </html>
    """

    return html

# =====================
# RUN
# =====================
if __name__ == "__main__":
    Thread(target=loop).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
