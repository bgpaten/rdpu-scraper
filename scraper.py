import re
import requests
from supabase import create_client, Client
import os
from datetime import datetime
from bs4 import BeautifulSoup

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# GOLD
PRICE_ID_GOLD = 1
ASSET_ID_GOLD = 4
URL = "https://pluang.com/asset/gold"


def extract_price(text):
    """Ekstrak harga dari teks seperti 'Rp2.079.258/g'"""
    match = re.search(r"Rp\s?([\d\.]+)", text)
    if not match:
        return None
    return float(match.group(1).replace(".", ""))


try:
    res = requests.get(URL, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    price_value = None

    # 1️⃣ Coba cari langsung <h5> yang biasa dipakai
    h5s = soup.find_all("h5")
    for h5 in h5s:
        price_value = extract_price(h5.get_text(strip=True))
        if price_value:
            break

    # 2️⃣ Kalau gagal, coba cari semua elemen yang mengandung "Rp" + "/g"
    if not price_value:
        all_text = soup.get_text()
        price_value = extract_price(all_text)

    if not price_value:
        raise Exception("Harga emas tidak ditemukan di halaman Pluang")

    # Buat record untuk Supabase
    record = {
        "asset_id": ASSET_ID_GOLD,
        "price": round(price_value, 2),
        "price_time": datetime.utcnow().isoformat(),
    }

    response = supabase.table("prices").update(record).eq("id", PRICE_ID_GOLD).execute()
    print("✅ Gold price berhasil diupdate:", record)

except Exception as e:
    print("❌ Error Gold:", e)


# BTC
PRICE_ID_BTC = 3  # id row di tabel prices
ASSET_ID_BTC = 5  # id BTC di tabel assets
BTC_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=idr"

try:
    res = requests.get(BTC_URL, timeout=10)
    res.raise_for_status()
    data = res.json()

    if "bitcoin" not in data or "idr" not in data["bitcoin"]:
        raise Exception(f"API Error: {data}")

    btc_to_idr = data["bitcoin"]["idr"]

    record = {
        "asset_id": ASSET_ID_BTC,
        "price": btc_to_idr,
        "price_time": datetime.utcnow().isoformat(),
    }

    response = supabase.table("prices").update(record).eq("id", PRICE_ID_BTC).execute()
    print("✅ BTC price berhasil diupdate:", response)

except Exception as e:
    print("❌ Error BTC:", e)
