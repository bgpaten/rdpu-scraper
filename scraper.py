import requests
from bs4 import BeautifulSoup
import json
from supabase import create_client, Client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

URL = "https://bibit.id/reksadana/RD620/bri-seruni-pasar-uang-syariah"

try:
    res = requests.get(URL, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    script_tag = soup.find("script", id="__NEXT_DATA__", type="application/json")
    data = json.loads(script_tag.string)

    productDetail = data.get("props", {}).get("pageProps", {}).get("productDetail", {})
    nav = productDetail.get("nav", {})
    aum = productDetail.get("aum", {})

    if nav and aum:
        nav_value = nav.get("value")
        nav_date = nav.get("date")
        aum_value = aum.get("value")

        response = (
            supabase.table("rdpu_prices")
            .insert({"date": nav_date, "nav_value": nav_value, "aum_value": aum_value})
            .execute()
        )

        print("✅ Data berhasil disimpan ke Supabase:", response)
    else:
        print("⚠️ NAV atau AUM tidak ditemukan")

except Exception as e:
    print("❌ Error:", e)
