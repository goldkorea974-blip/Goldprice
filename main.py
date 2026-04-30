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
# CLEAN
# =====================
def D(x):
    return Decimal(x.replace(",", "").strip())

# =====================
# SNAPSHOT
# =====================
def get_snapshot():
    try:
        html = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("div", class_="price-item")

        data = {}

        for item in items:
            title = item.find("span", class_="font-medium")
            nums = item.find_all("span", class_="number-font")

            if not title or len(nums) < 2:
                continue

            name = title.text.strip()

            if "عيار" in name:
                sell = float(D(nums[0].text))
                buy = float(D(nums[1].text))

                data[name] = {"sell": sell, "buy": buy}

        return data

    except Exception as e:
        log(f"Snapshot error: {e}")
        return {}

# =====================
# ANALYSIS (REFERENCE + CONFIDENCE)
# =====================
karat_map = {"24": 24, "21": 21, "18": 18, "14": 14}

def analyze(data):
    gold = {k: v for k, v in data.items() if "عيار" in k}

    scores = {}

    for ref in gold:
        ref_k = karat_map[ref.split()[1]]

        errors = []

        for k in gold:
            if k == ref:
                continue

            k_k = karat_map[k.split()[1]]
            estimated = gold[k]["sell"] * (ref_k / k_k)

            errors.append(abs(gold[ref]["sell"] - estimated))

        scores[ref] = sum(errors) / len(errors) if errors else 9999

    best_ref = min(scores, key=scores.get)

    max_error = max(scores.values()) if scores else 1

    confidence = {
        k: max(0, 100 - (scores[k] / max_error * 100))
        for k in scores
    }

    return best_ref, confidence

# =====================
# FORMAT MESSAGE
# =====================
def format_msg(data, confidence, ref):
    msg = "💎 <b>Smart Gold System</b>\n\n"
    msg += f"🧠 المرجع: <b>{ref}</b>\n\n"
    msg += "━━━━━━━━━━━━━━\n"

    for k, v in data.items():
        if "عيار" in k:
            c = confidence.get(k, 0)
            msg += f"🔸 <b>{k}</b> ({c:.1f}%)\n"
            msg += f"🟢 بيع: {v['sell']} | 🔴 شراء: {v['buy']}\n"
            msg += "──────────────\n"

    msg += "━━━━━━━━━━━━━━\n"
    return msg

# =====================
# TELEGRAM
# =====================
def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHANNEL,
        "text": msg,
        "parse_mode": "HTML"
    })

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

            ref, confidence = analyze(data)

            # ⚠️ بدل المنع: مجرد تنبيه داخلي
            avg_conf = sum(confidence.values()) / len(confidence)
            if avg_conf < 60:
                log("⚠️ Market unstable (but still sending)")

            page_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
            now = time.time()

            if last_hash is None:
                send(format_msg(data, confidence, ref))
                last_hash = page_hash
                last_sent_time = now

            elif page_hash != last_hash and (now - last_sent_time) > 5:
                send(format_msg(data, confidence, ref))
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
    return "💎 Smart Gold Running"

@app.route("/api")
def api():
    return jsonify(get_snapshot())

# =====================
# START
# =====================
if __name__ == "__main__":
    Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
