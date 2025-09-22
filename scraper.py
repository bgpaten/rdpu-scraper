import re
import requests
from supabase import create_client, Client
import os
from datetime import datetime
from bs4 import BeautifulSoup
import sys

# Selenium imports dengan error handling untuk GitHub Actions
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    import time

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium not available, falling back to requests")

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print(
        "❌ Error: SUPABASE_URL dan SUPABASE_KEY harus diset di environment variables"
    )
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Constants
PRICE_ID_GOLD = 1
ASSET_ID_GOLD = 4
PRICE_ID_BTC = 3
ASSET_ID_BTC = 5
URL = "https://pluang.com/asset/gold"
BTC_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=idr"


def setup_chrome_driver():
    """Setup Chrome driver untuk GitHub Actions"""
    if not SELENIUM_AVAILABLE:
        return None

    chrome_options = Options()

    # Options untuk GitHub Actions (headless environment)
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")  # Speed up loading
    chrome_options.add_argument("--disable-javascript")  # Jika tidak butuh JS interaksi

    # User agent untuk avoid detection
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    )

    # Experimental options
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(f"❌ Failed to setup Chrome driver: {e}")
        return None


def extract_price_advanced(text):
    """Ekstrak harga dengan pattern yang lebih robust"""
    if not text:
        return None

    # Clean text
    text = re.sub(r"\s+", " ", text.strip())

    # Multiple patterns untuk harga Indonesia
    patterns = [
        r"Rp\s?([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)",  # Rp2.122.485 atau Rp2.122.485,00
        r"([0-9]{1,3}(?:\.[0-9]{3})*)/g",  # 2.122.485/g
        r"([0-9]{7,})",  # Raw number 2122485
        r"Rp\s?([0-9,]+)",  # Rp2,122,485
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                # Clean the number - handle both . and , as thousand separators
                clean_number = match.replace(".", "").replace(",", "")
                price = float(clean_number)

                # Validasi range harga emas yang masuk akal (1-5 juta per gram)
                if 1000000 <= price <= 5000000:
                    return price
            except ValueError:
                continue

    return None


def scrape_gold_with_selenium():
    """Scrape harga emas menggunakan Selenium"""
    driver = None
    try:
        print("🚀 Starting Selenium scraper...")
        driver = setup_chrome_driver()

        if not driver:
            return None

        print("🌐 Loading Pluang gold page...")
        driver.get(URL)

        # Wait for page load
        time.sleep(5)

        # Try multiple strategies to find price
        strategies = [
            # Strategy 1: Look for h5 elements
            lambda d: d.find_elements(By.TAG_NAME, "h5"),
            # Strategy 2: Look for elements containing "Rp"
            lambda d: d.find_elements(By.XPATH, "//*[contains(text(), 'Rp')]"),
            # Strategy 3: Look for price-related classes
            lambda d: d.find_elements(
                By.CSS_SELECTOR, "[class*='price'], [class*='value'], [class*='amount']"
            ),
            # Strategy 4: Look for elements with "/g"
            lambda d: d.find_elements(By.XPATH, "//*[contains(text(), '/g')]"),
        ]

        found_prices = []

        for i, strategy in enumerate(strategies, 1):
            try:
                print(f"🔍 Trying strategy {i}...")
                elements = strategy(driver)

                for element in elements:
                    try:
                        text = element.text.strip()
                        if text and len(text) < 100:  # Avoid very long texts
                            price = extract_price_advanced(text)
                            if price:
                                found_prices.append((price, text, f"strategy_{i}"))
                                print(
                                    f"💰 Found candidate: {price:,.0f} from '{text}' (strategy {i})"
                                )
                    except Exception:
                        continue

            except Exception as e:
                print(f"❌ Strategy {i} failed: {e}")
                continue

        # Return the most reasonable price (usually the highest recent price)
        if found_prices:
            # Sort by price and take the highest one (most likely to be current)
            best_price = max(found_prices, key=lambda x: x[0])
            print(f"✅ Selected price: {best_price[0]:,.0f} from {best_price[2]}")
            return best_price[0]

        # Fallback: scan entire page source
        print("🔄 Fallback: scanning page source...")
        page_text = driver.page_source
        price = extract_price_advanced(page_text)

        if price:
            print(f"✅ Fallback found: {price:,.0f}")
            return price

        return None

    except Exception as e:
        print(f"❌ Selenium scraper error: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def scrape_gold_fallback():
    """Fallback scraper menggunakan requests (original method)"""
    print("🔄 Using fallback scraper (requests)...")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        res = requests.get(URL, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # Try multiple extraction methods
        price_value = None

        # Method 1: h5 tags
        h5s = soup.find_all("h5")
        for h5 in h5s:
            price_value = extract_price_advanced(h5.get_text(strip=True))
            if price_value:
                break

        # Method 2: elements with price-related classes
        if not price_value:
            price_elements = soup.find_all(
                attrs={"class": re.compile(r"(price|value|amount)", re.I)}
            )
            for elem in price_elements:
                price_value = extract_price_advanced(elem.get_text(strip=True))
                if price_value:
                    break

        # Method 3: scan all text
        if not price_value:
            all_text = soup.get_text()
            price_value = extract_price_advanced(all_text)

        return price_value

    except Exception as e:
        print(f"❌ Fallback scraper error: {e}")
        return None


def update_gold_price():
    """Update gold price with multiple fallback strategies"""
    print("\n" + "=" * 50)
    print("🥇 SCRAPING GOLD PRICE")
    print("=" * 50)

    price_value = None

    # Strategy 1: Selenium (if available)
    if SELENIUM_AVAILABLE:
        price_value = scrape_gold_with_selenium()

    # Strategy 2: Fallback to requests
    if not price_value:
        price_value = scrape_gold_fallback()

    if not price_value:
        raise Exception("❌ Harga emas tidak ditemukan dengan semua metode")

    # Save to Supabase
    record = {
        "asset_id": ASSET_ID_GOLD,
        "price": round(price_value, 2),
        "price_time": datetime.utcnow().isoformat(),
    }

    response = supabase.table("prices").update(record).eq("id", PRICE_ID_GOLD).execute()

    if response.data:
        print(f"✅ Gold price berhasil diupdate: Rp{price_value:,.0f}")
        print(f"📊 Record: {record}")
    else:
        raise Exception(f"❌ Failed to update Supabase: {response}")


def update_btc_price():
    """Update BTC price (unchanged from original)"""
    print("\n" + "=" * 50)
    print("₿ SCRAPING BTC PRICE")
    print("=" * 50)

    try:
        res = requests.get(BTC_URL, timeout=10)
        res.raise_for_status()
        data = res.json()

        if "bitcoin" not in data or "idr" not in data["bitcoin"]:
            raise Exception(f"❌ API Error: {data}")

        btc_to_idr = data["bitcoin"]["idr"]

        record = {
            "asset_id": ASSET_ID_BTC,
            "price": btc_to_idr,
            "price_time": datetime.utcnow().isoformat(),
        }

        response = (
            supabase.table("prices").update(record).eq("id", PRICE_ID_BTC).execute()
        )

        if response.data:
            print(f"✅ BTC price berhasil diupdate: Rp{btc_to_idr:,.0f}")
        else:
            raise Exception(f"❌ Failed to update BTC: {response}")

    except Exception as e:
        print(f"❌ Error BTC: {e}")
        raise


def main():
    """Main function"""
    print("🚀 Starting Price Scraper")
    print(f"⏰ Time: {datetime.now()}")
    print(f"🔧 Selenium Available: {SELENIUM_AVAILABLE}")

    success_count = 0

    # Update Gold Price
    try:
        update_gold_price()
        success_count += 1
    except Exception as e:
        print(f"❌ Gold update failed: {e}")

    # Update BTC Price
    try:
        update_btc_price()
        success_count += 1
    except Exception as e:
        print(f"❌ BTC update failed: {e}")

    print(f"\n📊 Summary: {success_count}/2 prices updated successfully")

    if success_count == 0:
        sys.exit(1)  # Exit with error if nothing succeeded


if __name__ == "__main__":
    main()
