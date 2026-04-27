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

last_sent_value = None

# =====================
# CLEAN DECIMAL
# =====================
def D(x):
    return Decimal(x.replace(",", "").strip())

# =====================
# SNAPSHOT ENGINE
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

        # ===== GOLD PRICES =====
        if "عيار" in name and len(nums) >= 2:
            buy = D(nums[0].text)
            sell = D(nums[1].text)

            data[name] = {
                "buy": buy,
                "sell": sell
            }

            if "24" in name:
                gram_24 = sell

        # ===== OUNCE =====
        if "أوقية" in name:
            ounce = D(nums[0].text)

    # =====================
    # DOLLAR SAGHA (PRECISION)
    # =====================
    dollar = None

    if gram_24 and ounce:
        raw = (gram_24 * Decimal("31.103")) / ounce
        dollar = raw.quantize(Decimal("0.01"))
        data["دولار الصاغة"] = dollar

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

    msg += "━━━━━━━━━━━━━━\n⚡ Precision Engine"

    return msg

# =====================
# LOOP + VERIFIER
# =====================
while True:
    try:
        data, dollar = get_snapshot()

        # =====================
        # VERIFICATION
        # =====================
        if dollar is not None:

            if last_sent_value is not None:
                diff = abs(dollar - last_sent_value)

                if diff > Decimal("0.01"):
                    print("⚠️ Difference detected:", diff)

            # =====================
            # SEND ONLY IF CHANGED
            # =====================
            if dollar != last_sent_value:
                send(format_msg(data))
                last_sent_value = dollar

    except Exception as e:
        print("Error:", e)

    time.sleep(60)
