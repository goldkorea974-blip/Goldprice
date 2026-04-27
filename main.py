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

last_data = None

# =====================
# CLEAN NUMBER
# =====================
def D(x):
    return Decimal(x.replace(",", "").strip())

# =====================
# FETCH DATA
# =====================
def get_snapshot():
    headers = {"User-Agent": "Mozilla/5.0"}
    html = requests.get(URL, headers=headers, timeout=10).text

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

        # ===== GOLD =====
        if "عيار" in name and len(nums) >= 2:
            buy = D(nums[0].text)
            sell = D(nums[1].text)

            data[name] = {
                "بيع": float(sell),
                "شراء": float(buy)
            }

            if "24" in name:
                gram_24 = sell

        # ===== OUNCE =====
        if "أوقية" in name:
            ounce = D(nums[0].text)
            data["الأوقية العالمية"] = float(ounce)

    # =====================
    # DOLLAR SAGHA
    # =====================
    if gram_24 and ounce:
        raw = (gram_24 * Decimal("31.103")) / ounce
        data["دولار الصاغة"] = float(raw.quantize(Decimal("0.01")))

    return data

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
def format(data):
    msg = "💎 <b>تحديث أسعار الذهب</b>\n\n"
    msg += "━━━━━━━━━━━━━━\n"

    for k, v in data.items():
        if isinstance(v, dict):
            msg += f"🔸 {k}\n"
            msg += f"بيع: {v['بيع']} | شراء: {v['شراء']}\n"
            msg += "──────────────\n"
        else:
            msg += f"📌 {k}: {v}\n"

    msg += "━━━━━━━━━━━━━━\n⚡ تحديث تلقائي"

    return msg

# =====================
# LOOP
# =====================
while True:
    try:
        data = get_snapshot()

        # ✔ بدون global هنا
        if data != last_data:
            send(format(data))
            last_data = data

    except Exception as e:
        print("Error:", e)

    time.sleep(60)
