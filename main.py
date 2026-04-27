import os
import time
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, send_file
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# =====================
# CONFIG
# =====================
TOKEN = "8165343576:AAGr_uWTBUMGCgcdahiCicHN3DehLaBOUf0"
CHANNEL_ID = "@your_channel"

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# =====================
# CACHE
# =====================
cache = {"data": None, "time": 0}
CACHE_TIME = 60  # ثانية

# =====================
# SCRAPING FUNCTION
# =====================
def get_all_prices():
    global cache

    # استخدام الكاش
    if time.time() - cache["time"] < CACHE_TIME:
        return cache["data"]

    url = "https://edahabapp.com/"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, "html.parser")

        prices = {}
        items = soup.find_all("div", class_="price-item")

        for item in items:
            title_span = item.find("span", class_="font-medium")
            if not title_span:
                continue

            title = title_span.text.strip()
            numbers = item.find_all("span", class_="number-font")

            if len(numbers) == 0:
                continue

            if "عيار" in title or "الذهب" in title:
                if len(numbers) >= 2:
                    prices[title] = {
                        "بيع": numbers[0].text.strip(),
                        "شراء": numbers[1].text.strip()
                    }
            else:
                prices[title] = numbers[0].text.strip()

        cache = {"data": prices, "time": time.time()}
        return prices

    except Exception as e:
        return {"error": str(e)}

# =====================
# FLASK API
# =====================
@app.route("/api/prices")
def api_prices():
    return jsonify(get_all_prices())

@app.route("/")
def home():
    return "Gold API is running..."

# =====================
# TELEGRAM BOT
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("البوت شغال 💰")

async def send_prices(context: ContextTypes.DEFAULT_TYPE):
    data = get_all_prices()

    if not data:
        return

    msg = "💰 أسعار الذهب:\n\n"

    for k, v in data.items():
        if isinstance(v, dict):
            msg += f"{k}\nبيع: {v['بيع']} | شراء: {v['شراء']}\n\n"
        else:
            msg += f"{k}: {v}\n"

    await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)

# =====================
# RUN BOTH
# =====================
def run_bot():
    app_bot = ApplicationBuilder().token(TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start))

    job = app_bot.job_queue
    job.run_repeating(send_prices, interval=300, first=10)

    app_bot.run_polling()

# =====================
# MAIN
# =====================
if __name__ == "__main__":
    from threading import Thread

    # شغل البوت في Thread
    Thread(target=run_bot).start()

    # شغل Flask
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
