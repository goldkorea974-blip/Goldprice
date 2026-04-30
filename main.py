import os
import time
import requests
from bs4 import BeautifulSoup
from decimal import Decimal, getcontext
from flask import Flask, jsonify
from threading import Thread
from datetime import datetime

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

last_sent_value = None
end_sent = False
start_sent = False

# =====================
# LOGGING
# =====================
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# =====================
# CLEAN DECIMAL
# =====================
def D(x):
    return Decimal(x.replace(",", "").strip())

# =====================
# SNAPSHOT ENGINE (WITH RETRY)
# =====================
def get_snapshot(retries=3):
    for attempt in range(retries):
        try:
            log(f"Fetching data (attempt {attempt+1})")

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

                # GOLD
                if "عيار" in name and len(nums) >= 2:
                    buy = D(nums[0].text)
                    sell = D(nums[1].text)

                    data[name] = {
                        "buy": str(buy),
                        "sell": str(sell)
                    }

                    if "24" in name:
                        gram_24 = buy

                # OUNCE
                if "أوقية" in name or "اونصة" in name or "ounce" in name.lower():
                    ounce = D(nums[0].text)
                    data["الأوقية العالمية"] = str(ounce)

            dollar = None
            if gram_24 and ounce:
                raw = (gram_24 * Decimal("31.1034768")) / ounce
                dollar = raw
                data["دولار الصاغة"] = str(round(dollar, 2))

            log("Snapshot success")
            return data, dollar

        except Exception as e:
            log(f"Snapshot error: {e}")
            time.sleep(2)

    log("Snapshot FAILED after retries ❌")
    return {}, None

# =====================
# TELEGRAM SEND
# =====================
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHANNEL,
            "text": msg,
            "parse_mode": "HTML"
        })
        log("Message sent ✔️")
    except Exception as e:
        log(f"Send error: {e}")

# =====================
# FORMAT LIVE MESSAGE
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

    msg += "━━━━━━━━━━━━━━\n"
    msg += '🌐 <a href="https://andriagold.netlify.app/">افتح الموقع</a>\n'
    msg += "━━━━━━━━━━━━━━\n"
    msg += '📢 <a href="https://t.me/AndreaGold">تعالا شوف شغلنا</a>\n'

    return msg

# =====================
# FORMAT END DAY MESSAGE
# =====================
def format_end_msg(data):
    msg = "📉 <b>نهاية تداول اليوم</b>\n\n"
    msg += "🏁 الأسعار قفلت على:\n"
    msg += "━━━━━━━━━━━━━━\n"

    for k, v in data.items():
        if isinstance(v, dict):
            msg += f"🔸 {k}\n"
            msg += f"بيع: {v['sell']} | شراء: {v['buy']}\n"
            msg += "──────────────\n"

    msg += "━━━━━━━━━━━━━━\n"

    return msg

# =====================
# LOOP
# =====================
def loop():
    global last_sent_value, end_sent, start_sent

    while True:
        try:
            now = datetime.now()
            hour = now.hour

            log(f"Loop tick | hour={hour} start_sent={start_sent}")

            # 🟢 START (10 AM)
            if 10 <= hour <= 23:

                if hour >= 10 and not start_sent:
                    log("🚀 Sending START message")

                    data, dollar = get_snapshot()

                    if data:
                        send(format_msg(data))
                        last_sent_value = dollar
                        start_sent = True
                        end_sent = False
                        log("🟢 START sent")
                    else:
                        log("❌ START skipped (no data)")

                else:
                    data, dollar = get_snapshot()

                    if dollar is not None:

                        if last_sent_value is not None:
                            diff = abs(dollar - last_sent_value)

                            if diff > Decimal("0.05"):
                                log(f"⚠️ Change detected: {diff}")

                        if dollar != last_sent_value:
                            send(format_msg(data))
                            last_sent_value = dollar
                            log("📤 Update sent")

            # 🌙 END (12 AM)
            elif hour == 0 and not end_sent:
                log("📉 Sending END message")

                data, _ = get_snapshot()
                send(format_end_msg(data))

                end_sent = True
                start_sent = False

                log("📉 END sent")

        except Exception as e:
            log(f"Loop error: {e}")

        time.sleep(60)

# =====================
# API
# =====================
@app.route("/")
def home():
    return "💎 Gold Bot Running ✅"

@app.route("/api")
def api():
    data, _ = get_snapshot()
    return jsonify(data)

# =====================
# START
# =====================
if __name__ == "__main__":
    Thread(target=loop, daemon=True).start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
