import re
import requests
from supabase import create_client, Client
import os
from datetime import datetime
import sys
import time

# --- Selenium untuk emas & XIPI ---
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium not available, fallback disabled for gold & XIPI")

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

# 👉 BMRI – SESUAIKAN DENGAN DB KAMU
PRICE_ID_BMRI = 4
ASSET_ID_BMRI = 8

# 👉 MDKA – SESUAIKAN DENGAN DB KAMU
PRICE_ID_MDKA = 5 
ASSET_ID_MDKA = 9  

# 👉 ETF XIPI – SESUAIKAN DENGAN DB KAMU (DI-COMMENT)
# PRICE_ID_XIPI = 4
# ASSET_ID_XIPI = 6

URL_GOLD = "https://pluang.com/asset/gold"
URL_BTC = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=idr"

# Link Google Finance XIPI (sesuai yang kamu kasih)
# URL_XIPI = "https://www.google.com/finance/quote/XIJI:IDX?sa=X&ved=2ahUKEwiXosCPtJuRAxVIzzgGHUA8InIQ3ecFegQIGxAb"

# Link Ajaib BMRI
URL_BMRI = "https://ajaib.co.id/saham/aset/BMRI"

# Link Ajaib MDKA
URL_MDKA = "https://ajaib.co.id/saham/aset/MDKA"


# -------------------------------
# UTILS
# -------------------------------
def extract_price(text: str):
    """Ekstrak angka harga dari teks Rp (range besar untuk emas)"""
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
        
        # Tunggu render dengan lebih sabar
        time.sleep(8)

        # 1. Coba selector spesifik yang ditemukan dari inspect/debug
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, ".AssetPriceGraph_price-text__28CyY")
            for el in elements:
                text = el.text.strip()
                if "Rp" in text:
                    price = extract_price(text)
                    if price:
                        print(f"💰 Gold price found (selector): Rp{price:,.0f}/g ({text})")
                        return price
        except Exception:
            pass

        # 2. Fallback: Cari elemen <h5> yang ada Rp (logika lama)
        elements = driver.find_elements(By.XPATH, "//h5")
        for el in elements:
            text = el.text.strip()
            if "Rp" in text:
                price = extract_price(text)
                if price:
                    print(f"💰 Gold price found (h5): Rp{price:,.0f}/g ({text})")
                    return price

        # 3. Fallback: cari semua elemen dengan Rp dan /g
        all_elements = driver.find_elements(By.XPATH, "//*[contains(text(),'Rp')]")
        for el in all_elements:
            text = el.text.strip()
            if "/g" in text:
                price = extract_price(text)
                if price:
                    print(f"💰 Gold price fallback (/g): Rp{price:,.0f}/g ({text})")
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


# # -------------------------------
# # XIPI ETF SCRAPER (GOOGLE FINANCE) - COMMENTED
# # -------------------------------
# def extract_xipi_price(text: str) -> float | None:
#     """
#     Ekstrak harga XIPI dari teks seperti:
#     - 'Rp221,00'
#     - 'Rp221.00'
#     dan kembalikan sebagai 221.0
#     """
#     if not text:
#         return None
#
#     # Ambil hanya bagian setelah 'Rp'
#     text = text.replace("Rp", "").strip()
#
#     # Sisakan hanya angka, titik, koma
#     clean = re.sub(r"[^0-9\.,]", "", text)
#
#     if not clean:
#         return None
#
#     # Normalisasi:
#     # - kalau ada koma -> anggap koma = desimal
#     # - buang pemisah ribuan
#     if "," in clean and "." in clean:
#         # contoh '1.234,56' -> '1234.56'
#         clean = clean.replace(".", "").replace(",", ".")
#     elif "," in clean:
#         # contoh '221,00' -> '221.00'
#         clean = clean.replace(".", "").replace(",", ".")
#     else:
#         # contoh '221.00' -> biarin
#         pass
#
#     try:
#         value = float(clean)
#         # Harga ETF di IDX biasanya integer, buletin aja
#         return round(value)
#     except ValueError:
#         return None
#
#
# def scrape_xipi_price():
#     """Scraping harga ETF XIPI dari Google Finance"""
#     driver = None
#     try:
#         if not SELENIUM_AVAILABLE:
#             raise Exception("Selenium not available")
#
#         driver = setup_driver()
#         driver.get(URL_XIPI)
#         time.sleep(6)  # tunggu chart & harga utama render
#
#         # Elemen harga utama biasanya: <div class="YMlKec fxKbKc">Rp221,00</div>
#         elements = driver.find_elements(By.CSS_SELECTOR, "div.YMlKec.fxKbKc")
#         for el in elements:
#             text = el.text.strip()
#             if text.startswith("Rp"):
#                 price = extract_xipi_price(text)
#                 if price is not None:
#                     print(f"📈 XIPI price found: {text} -> {price}")
#                     return price
#
#         # Fallback cari semua div yang mengandung Rp
#         all_divs = driver.find_elements(
#             By.XPATH, "//div[contains(@class,'YMlKec')][contains(.,'Rp')]"
#         )
#         for el in all_divs:
#             text = el.text.strip()
#             price = extract_xipi_price(text)
#             if price is not None:
#                 print(f"📈 XIPI price fallback: {text} -> {price}")
#                 return price
#
#         return None
#
#     except Exception as e:
#         print(f"❌ XIPI scraper error: {e}")
#         return None
#     finally:
#         if driver:
#             driver.quit()
#
#
# def update_xipi_price():
#     print("\n" + "=" * 50)
#     print("📊 SCRAPING XIPI ETF PRICE")
#     print("=" * 50)
#
#     price_value = scrape_xipi_price()
#     if not price_value:
#         raise Exception("❌ Harga XIPI gagal diambil")
#
#     record = {
#         "id": PRICE_ID_XIPI,
#         "asset_id": ASSET_ID_XIPI,
#         "price": round(price_value, 2),
#         "price_time": datetime.utcnow().isoformat(),
#     }
#
#     response = supabase.table("prices").upsert(record, on_conflict=["id"]).execute()
#     if response.data:
#         print(f"✅ XIPI price upserted: Rp{price_value:,.0f}")
#     else:
#         raise Exception(f"❌ Failed to upsert XIPI: {response}")


# -------------------------------
# BMRI STOCK SCRAPER (AJAIB)
# -------------------------------
def extract_bmri_price(text: str) -> float | None:
    """
    Ekstrak harga BMRI dari teks seperti:
    - '4,770'
    dan kembalikan sebagai 4770.0
    """
    if not text:
        return None

    # Bersihkan dari semua kecuali angka, titik, dan koma
    clean = re.sub(r"[^0-9\.,]", "", text)

    # Pada Ajaib, format saham biasanya ribuan pakai koma (4,770)
    # Kita buang koma untuk jadi angka bersih
    clean = clean.replace(",", "")

    try:
        return float(clean)
    except ValueError:
        return None


def scrape_bmri_price():
    """Scraping harga saham BMRI dari Ajaib"""
    driver = None
    try:
        if not SELENIUM_AVAILABLE:
            raise Exception("Selenium not available")

        driver = setup_driver()
        driver.get(URL_BMRI)
        time.sleep(6)  # tunggu render

        # Sesuai hasil inspect: <span class="font-semibold mr-3 text-2xl">4,770</span>
        element = driver.find_element(By.CSS_SELECTOR, "span.font-semibold.mr-3.text-2xl")
        if element:
            text = element.text.strip()
            price = extract_bmri_price(text)
            if price is not None:
                print(f"📈 BMRI price found: {text} -> {price}")
                return price

        return None

    except Exception as e:
        print(f"❌ BMRI scraper error: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def update_bmri_price():
    print("\n" + "=" * 50)
    print("📈 SCRAPING BMRI STOCK PRICE")
    print("=" * 50)

    price_value = scrape_bmri_price()
    if not price_value:
        raise Exception("❌ Harga BMRI gagal diambil")

    record = {
        "id": PRICE_ID_BMRI,
        "asset_id": ASSET_ID_BMRI,
        "price": round(price_value, 2),
        "price_time": datetime.utcnow().isoformat(),
    }

    response = supabase.table("prices").upsert(record, on_conflict=["id"]).execute()
    if response.data:
        print(f"✅ BMRI price upserted: Rp{price_value:,.0f}")
    else:
        raise Exception(f"❌ Failed to upsert BMRI: {response}")


# -------------------------------
# MDKA STOCK SCRAPER (AJAIB)
# -------------------------------
def extract_mdka_price(text: str) -> float | None:
    """
    Ekstrak harga MDKA dari teks seperti:
    - '2,500'
    dan kembalikan sebagai 2500.0
    """
    if not text:
        return None

    # Bersihkan dari semua kecuali angka, titik, dan koma
    clean = re.sub(r"[^0-9\.,]", "", text)

    # Pada Ajaib, format saham biasanya ribuan pakai koma (4,770)
    # Kita buang koma untuk jadi angka bersih
    clean = clean.replace(",", "")

    try:
        return float(clean)
    except ValueError:
        return None


def scrape_mdka_price():
    """Scraping harga saham MDKA dari Ajaib"""
    driver = None
    try:
        if not SELENIUM_AVAILABLE:
            raise Exception("Selenium not available")

        driver = setup_driver()
        driver.get(URL_MDKA)
        time.sleep(6)  # tunggu render

        # Sesuai hasil inspect: <span class="font-semibold mr-3 text-2xl">...</span>
        element = driver.find_element(By.CSS_SELECTOR, "span.font-semibold.mr-3.text-2xl")
        if element:
            text = element.text.strip()
            price = extract_mdka_price(text)
            if price is not None:
                print(f"📈 MDKA price found: {text} -> {price}")
                return price

        return None

    except Exception as e:
        print(f"❌ MDKA scraper error: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def update_mdka_price():
    print("\n" + "=" * 50)
    print("📈 SCRAPING MDKA STOCK PRICE")
    print("=" * 50)

    price_value = scrape_mdka_price()
    if not price_value:
        raise Exception("❌ Harga MDKA gagal diambil")

    record = {
        "id": PRICE_ID_MDKA,
        "asset_id": ASSET_ID_MDKA,
        "price": round(price_value, 2),
        "price_time": datetime.utcnow().isoformat(),
    }

    response = supabase.table("prices").upsert(record, on_conflict=["id"]).execute()
    if response.data:
        print(f"✅ MDKA price upserted: Rp{price_value:,.0f}")
    else:
        raise Exception(f"❌ Failed to upsert MDKA: {response}")


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
        update_bmri_price()
        success += 1
    except Exception as e:
        print(f"❌ BMRI update failed: {e}")

    try:
        update_mdka_price()
        success += 1
    except Exception as e:
        print(f"❌ MDKA update failed: {e}")

    try:
        update_btc_price()
        success += 1
    except Exception as e:
        print(f"❌ BTC update failed: {e}")

    print(f"\n📊 Summary: {success}/4 updates succeeded")
    if success == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
