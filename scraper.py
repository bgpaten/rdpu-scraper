import re
import requests
from supabase import create_client, Client
import os
from datetime import datetime
import sys
import time

# --- Selenium untuk emas ---
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium not available, fallback disabled for gold")

# --- Supabase setup ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print(
        "❌ Error: SUPABASE_URL dan SUPABASE_KEY harus diset di environment variables"
    )
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Constants ---
PRICE_ID_GOLD = 1  # id row untuk emas
ASSET_ID_GOLD = 4
PRICE_ID_BTC = 3  # id row untuk BTC
ASSET_ID_BTC = 5

URL_GOLD = "https://pluang.com/asset/gold"
URL_BTC = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=idr"


# -------------------------------
# UTILS
# -------------------------------
def extract_price(text: str):
    """Ekstrak angka harga dari teks Rp"""
    if not text:
        return None

    text = re.sub(r"\s+", " ", text.strip())
    match = re.search(r"Rp\s*([0-9]{1,3}(?:\.[0-9]{3})+)", text)

    if match:
        clean_number = match.group(1).replace(".", "")
        try:
            price = float(clean_number)
            if 500000 <= price <= 10000000:  # range masuk akal
                return price
        except ValueError:
            return None
    return None


def setup_driver():
    """Setup Chrome headless"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/117.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


# -------------------------------
# GOLD SCRAPER
# -------------------------------
def scrape_gold_price():
    """Scraping harga emas utama dari Pluang"""
    driver = None
    try:
        if not SELENIUM_AVAILABLE:
            raise Exception("Selenium not available")

        driver = setup_driver()
        driver.get(URL_GOLD)
        time.sleep(6)  # tunggu render

        # Cari elemen <h5> yang ada Rp
        elements = driver.find_elements(By.XPATH, "//h5")
        for el in elements:
            text = el.text.strip()
            if "Rp" in text:
                price = extract_price(text)
                if price:
                    print(f"💰 Gold price found: Rp{price:,.0f}/g ({text})")
                    return price

        # fallback cari semua elemen dengan Rp
        all_elements = driver.find_elements(By.XPATH, "//*[contains(text(),'Rp')]")
        for el in all_elements:
            text = el.text.strip()
            if "/g" in text:
                price = extract_price(text)
                if price:
                    print(f"💰 Gold price fallback: Rp{price:,.0f}/g ({text})")
                    return price

        return None

    except Exception as e:
        print(f"❌ Gold scraper error: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def update_gold_price():
    print("\n" + "=" * 50)
    print("🥇 SCRAPING GOLD PRICE")
    print("=" * 50)

    price_value = scrape_gold_price()
    if not price_value:
        raise Exception("❌ Harga emas gagal diambil")

    record = {
        "id": PRICE_ID_GOLD,  # pakai id tabel
        "asset_id": ASSET_ID_GOLD,
        "price": round(price_value, 2),
        "price_time": datetime.utcnow().isoformat(),
    }

    response = supabase.table("prices").upsert(record, on_conflict=["id"]).execute()
    if response.data:
        print(f"✅ Gold price upserted: Rp{price_value:,.0f}")
    else:
        raise Exception(f"❌ Failed to upsert gold: {response}")


# -------------------------------
# BTC SCRAPER
# -------------------------------
def update_btc_price():
    print("\n" + "=" * 50)
    print("₿ SCRAPING BTC PRICE")
    print("=" * 50)

    try:
        res = requests.get(URL_BTC, timeout=10)
        res.raise_for_status()
        data = res.json()
        btc_to_idr = data["bitcoin"]["idr"]

        record = {
            "id": PRICE_ID_BTC,  # pakai id tabel
            "asset_id": ASSET_ID_BTC,
            "price": btc_to_idr,
            "price_time": datetime.utcnow().isoformat(),
        }

        response = supabase.table("prices").upsert(record, on_conflict=["id"]).execute()
        if response.data:
            print(f"✅ BTC price upserted: Rp{btc_to_idr:,.0f}")
        else:
            raise Exception(f"❌ Failed to upsert BTC: {response}")

    except Exception as e:
        print(f"❌ BTC update failed: {e}")
        raise


# -------------------------------
# MAIN
# -------------------------------
def main():
    print("🚀 Starting Scraper")
    print(f"⏰ Time: {datetime.now()}")
    print(f"🔧 Selenium Available: {SELENIUM_AVAILABLE}")

    success = 0
    try:
        update_gold_price()
        success += 1
    except Exception as e:
        print(f"❌ Gold update failed: {e}")

    try:
        update_btc_price()
        success += 1
    except Exception as e:
        print(f"❌ BTC update failed: {e}")

    print(f"\n📊 Summary: {success}/2 updates succeeded")
    if success == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
