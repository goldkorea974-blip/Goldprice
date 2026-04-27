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
import requests
from bs4 import BeautifulSoup
from decimal import Decimal, getcontext
import time

# 🔥 رفع الدقة الحسابية
getcontext().prec = 28

# =====================
# FETCH ONCE (SNAPSHOT)
# =====================
def fetch_snapshot():
    url = "https://edahabapp.com/"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=10)
    return BeautifulSoup(res.text, "html.parser")

# =====================
# SAFE NUMBER PARSER
# =====================
def clean_number(text):
    return Decimal(text.replace(",", "").strip())

# =====================
# ENGINE CORE
# =====================
def calculate_precision():
    soup = fetch_snapshot()

    items = soup.find_all("div", class_="price-item")

    gram_24 = None
    ounce_usd = None

    for item in items:
        title = item.find("span", class_="font-medium")
        numbers = item.find_all("span", class_="number-font")

        if not title or len(numbers) == 0:
            continue

        name = title.text.strip()

        # ===== GOLD 24 =====
        if "24" in name and len(numbers) >= 2:
            # نثبت النص قبل أي تحويل
            sell_text = numbers[1].text
            gram_24 = clean_number(sell_text)

        # ===== OUNCE =====
        if "أوقية" in name:
            ounce_text = numbers[0].text
            ounce_usd = clean_number(ounce_text)

    # =====================
    # PRECISION FORMULA
    # =====================
    if gram_24 and ounce_usd:
        raw = (gram_24 * Decimal("31.103")) / ounce_usd

        # final rounding فقط هنا
        dollar_sagha = raw.quantize(Decimal("0.01"))

        return {
            "gram_24": gram_24,
            "ounce_usd": ounce_usd,
            "dollar_sagha": float(dollar_sagha)
        }

    return None


# =====================
# TEST RUN
# =====================
while True:
    result = calculate_precision()

    if result:
        print("💎 GRAM 24:", result["gram_24"])
        print("🌍 OUNCE USD:", result["ounce_usd"])
        print("💵 DOLLAR SAGHA:", result["dollar_sagha"])
        print("━━━━━━━━━━━━━━")

    time.sleep(60)
