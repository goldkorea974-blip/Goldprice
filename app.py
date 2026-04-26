from flask import Flask, jsonify, send_file
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

def get_all_prices():
    url = "https://edahabapp.com/"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
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

    return prices

@app.route("/api/prices")
def prices_api():
    return jsonify(get_all_prices())

@app.route("/")
def index():
    return send_file("index.html")

import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))