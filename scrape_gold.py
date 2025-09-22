import re
import requests
from bs4 import BeautifulSoup

URL = "https://pluang.com/asset/gold"


def extract_price(text):
    match = re.search(r"Rp\s?([\d\.]+)", text)
    if not match:
        return None
    return float(match.group(1).replace(".", ""))


try:
    res = requests.get(URL, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    price_value = None

    # Coba cari harga di elemen <h5>
    for h5 in soup.find_all("h5"):
        price_value = extract_price(h5.get_text(strip=True))
        if price_value:
            break

    # Fallback → scan semua teks
    if not price_value:
        price_value = extract_price(soup.get_text())

    if price_value:
        print("✅ Harga emas terbaru:", price_value, "per gram")
    else:
        print("❌ Tidak menemukan harga")

except Exception as e:
    print("❌ Error:", e)
