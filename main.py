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

SITE_LINK = "https://andriagold.netlify.app/"
CHANNEL_LINK = "https://t.me/AndreaGold"

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
# CLEAN NUMBER
# =====================
def D(x):
    return Decimal(x.replace(",", "").strip())

# =====================
# KARAT MAP SAFE
# =====================
karat_map = {"24": 24, "21": 21, "18": 18, "14": 14}

def extract_karat(name):
    for k in karat_map:
        if k in name:
            return karat_map[k]
    return None

# =====================
# SNAPSHOT
# =====================
def get_snapshot():
    try:
        html = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("div", class_="price-item")

        data = {}

        gram_24 = None
        ounce = None

        for item in items:
            title = item.find("span", class_="font-medium")
            nums = item.find_all("span", class_="number-font")

            if not title:
                continue

            name = title.text.strip()

            # ================= GOLD =================
            if any(k in name for k in karat_map):
                if len(nums) >= 2:
                    sell = float(D(nums[0].text))
                    buy = float(D(nums[1].text))

                    data[name] = {"sell": sell, "buy": buy}

                    if "24" in name:
                        gram_24 = sell

            # ================= OUNCE =================
            if "أوقية" in name or "ounce" in name.lower():
                try:
                    ounce = float(D(nums[0].text))
                    data["الأوقية العالمية"] = ounce
                except:
                    pass

            # ================= USD =================
            if "الدولار" in name:
                try:
                    usd = float(D(nums[0].text))
                    data["الدولار الأمريكي"] = usd
                except:
                    pass

        # ================= GOLD USD =================
        if gram_24 and ounce:
            gold_usd = (gram_24 * 31.1034768) / ounce
            data["دولار الصاغة"] = round(gold_usd, 2)

        return data

    except Exception as e:
        log(f"Snapshot error: {e}")
        return {}

# =====================
# ANALYSIS ENGINE
# =====================
def analyze(data):
    gold = {k: v for k, v in data.items() if any(x in k for x in karat_map)}

    scores = {}

    for ref in gold:
        ref_k = extract_karat(ref)
        if not ref_k:
            continue

        errors = []

        for k in gold:
            if k == ref:
                continue

            k_k = extract_karat(k)
            if not k_k:
                continue

            estimated = gold[k]["sell"] * (ref_k / k_k)
            errors.append(abs(gold[ref]["sell"] - estimated))

        scores[ref] = sum(errors) / len(errors) if errors else 9999

    if not scores:
        return None, {}

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
        if isinstance(v, dict):
            c = confidence.get(k, 0)
            msg += f"🔸 <b>{k}</b> ({c:.1f}%)\n"
            msg += f"🟢 بيع: {v['sell']} | 🔴 شراء: {v['buy']}\n"
            msg += "──────────────\n"
        else:
            msg += f"📌 {k}: <b>{v}</b>\n"

    msg += "━━━━━━━━━━━━━━\n"
    return msg

# =====================
# TELEGRAM SEND (WITH BUTTONS)
# =====================
def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🌐 الموقع", "url": SITE_LINK},
                {"text": "📢 القناة", "url": CHANNEL_LINK}
            ]
        ]
    }

    requests.post(url, data={
        "chat_id": CHANNEL,
        "text": msg,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(keyboard)
    })

# =====================
# LOOP
# =====================
def loop():
    global last_hash, last_sent_time

    first_run = True

    while True:
        try:
            data = get_snapshot()
            if not data:
                time.sleep(5)
                continue

            ref, confidence = analyze(data)

            page_hash = hashlib.md5(
                json.dumps(data, sort_keys=True).encode()
            ).hexdigest()

            now = time.time()

            # أول رسالة
            if first_run:
                send(format_msg(data, confidence, ref))
                last_hash = page_hash
                last_sent_time = now
                first_run = False
                log("🚀 First update sent")

            # تحديث عند التغيير
            elif page_hash != last_hash and (now - last_sent_time) > 5:
                send(format_msg(data, confidence, ref))
                last_hash = page_hash
                last_sent_time = now
                log("🔄 Update sent")

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
