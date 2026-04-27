import requests
from bs4 import BeautifulSoup
from decimal import Decimal, getcontext
import time

# =====================
# CONFIG
# =====================
TOKEN = "8165343576:AAGr_uWTBUMGCgcdahiCicHN3DehLaBOUf0"
CHANNEL = "@AndriaGold"
URL = "https://edahabapp.com/"

getcontext().prec = 28

last_final_price = None

# =====================
# SAFE DECIMAL
# =====================
def D(x):
    return Decimal(x.replace(",", "").strip())

# =====================
# SNAPSHOT
# =====================
def fetch_snapshot():
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(URL, headers=headers, timeout=10).text

    soup = BeautifulSoup(html, "html.parser")
    items = soup.find_all("div", class_="price-item")

    gram_24 = None
    ounce = None

    data = {}

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
                "buy": buy,
                "sell": sell
            }

            if "24" in name:
                gram_24 = sell

        if "أوقية" in name:
            ounce = D(nums[0].text)

    return data, gram_24, ounce

# =====================
# STABLE CALC ENGINE
# =====================
def calculate_stable():
    data, gram_24, ounce = fetch_snapshot()

    if not gram_24 or not ounce:
        return None

    raw = (gram_24 * Decimal("31.103")) / ounce
    dollar = raw.quantize(Decimal("0.01"))

    # =====================
    # SELF CORRECTION LOGIC
    # =====================
    global last_final_price

    if last_final_price is not None:
        diff = abs(dollar - last_final_price)

        # ⚠️ لو الفرق صغير جدًا → نثبت القيمة السابقة
        if diff <= Decimal("0.05"):
            dollar = last_final_price

    last_final_price = dollar

    data["دولار الصاغة"] = dollar

    return data

# =====================
# FORMAT MESSAGE
# =====================
def format_msg(data):
    msg = "💎 <b>Gold Stable Engine</b>\n\n"
    msg += "━━━━━━━━━━━━━━\n"

    for k, v in data.items():
        if isinstance(v, dict):
            msg += f"🔸 {k}\n"
            msg += f"بيع: {v['sell']} | شراء: {v['buy']}\n"
            msg += "──────────────\n"
        else:
            msg += f"📌 {k}: {v}\n"

    msg += "━━━━━━━━━━━━━━\n⚡ Self-Corrected Stable Price"

    return msg

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
# LOOP
# =====================
while True:
    try:
        result = calculate_stable()

        if result:
            send(format_msg(result))

    except Exception as e:
        print("Error:", e)

    time.sleep(60)
