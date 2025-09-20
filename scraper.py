import requests
from supabase import create_client, Client
import os
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# GOLD
GOLD_ID = 1  # id row di tabel prices untuk Gold
URL = "https://api.exchangerate.host/convert?access_key=d4fe6549a0d4c4c4a0e919dcd6698dd7&from=XAU&to=IDR&amount=1"

try:
    res = requests.get(URL, timeout=10)
    res.raise_for_status()
    data = res.json()

    if "result" not in data or data["result"] is None:
        raise Exception(f"API Error: {data}")

    xau_to_idr = data["result"]
    gram_per_xau = 31.1034768
    price_per_gram = xau_to_idr / gram_per_xau

    record = {
        "price": round(price_per_gram, 2),
        "price_time": datetime.utcnow().isoformat(),
    }

    response = supabase.table("prices").update(record).eq("id", GOLD_ID).execute()
    print("✅ Gold price berhasil diupdate:", response)

except Exception as e:
    print("❌ Error Gold:", e)


# BTC
BTC_ID = 3  # id row di tabel prices untuk BTC
BTC_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=idr"

try:
    res = requests.get(BTC_URL, timeout=10)
    res.raise_for_status()
    data = res.json()

    if "bitcoin" not in data or "idr" not in data["bitcoin"]:
        raise Exception(f"API Error: {data}")

    btc_to_idr = data["bitcoin"]["idr"]

    record = {
        "price": btc_to_idr,
        "price_time": datetime.utcnow().isoformat(),
    }

    response = supabase.table("prices").update(record).eq("id", BTC_ID).execute()
    print("✅ BTC price berhasil diupdate:", response)

except Exception as e:
    print("❌ Error BTC:", e)
