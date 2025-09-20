import requests
from supabase import create_client, Client
import os
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

URL = "https://api.exchangerate.host/convert?access_key=d4fe6549a0d4c4c4a0e919dcd6698dd7&from=XAU&to=IDR&amount=1"

try:
    res = requests.get(URL, timeout=10)
    res.raise_for_status()
    data = res.json()

    if "result" not in data or data["result"] is None:
        raise Exception(f"API Error: {data}")

    xau_to_idr = data["result"]  # harga 1 XAU dalam Rupiah
    gram_per_xau = 31.1034768
    price_per_gram = xau_to_idr / gram_per_xau

    record = {
        "asset_id": 4,  # id aset Gold di tabel assets
        "price": round(price_per_gram, 2),
        "price_time": datetime.utcnow().isoformat(),  # waktu harga
    }

    response = supabase.table("prices").insert(record).execute()

    print("✅ Data berhasil disimpan ke Supabase:", response)

except Exception as e:
    print("❌ Error:", e)
