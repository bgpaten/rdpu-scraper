from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import re
import time


def setup_driver():
    """Setup Chrome driver dengan options yang optimal"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Hapus ini jika ingin melihat browser
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def extract_price_from_text(text):
    """Extract price dari text dengan berbagai format"""
    # Hapus whitespace dan normalize
    text = re.sub(r"\s+", " ", text.strip())

    # Pattern untuk menangkap harga Indonesia
    patterns = [
        r"Rp\s*([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)",  # Rp2.122.485
        r"([0-9]{1,3}(?:\.[0-9]{3})*(?:,[0-9]{2})?)\s*/g",  # 2.122.485/g
        r"([0-9]{7,})",  # Angka besar tanpa separator
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                # Konversi ke float (hapus titik sebagai thousand separator)
                clean_number = match.replace(".", "").replace(",", ".")
                price = float(clean_number)
                # Validasi range harga emas yang masuk akal (1-5 juta per gram)
                if 1000000 <= price <= 5000000:
                    return price
            except ValueError:
                continue

    return None


def scrape_gold_price():
    """Main function untuk scraping harga emas"""
    driver = None
    try:
        print("🚀 Memulai browser...")
        driver = setup_driver()

        print("🌐 Mengakses Pluang...")
        driver.get("https://pluang.com/asset/gold")

        # Tunggu halaman load
        print("⏳ Menunggu halaman load...")
        time.sleep(5)

        # Tunggu elemen harga muncul
        wait = WebDriverWait(driver, 10)

        # Strategi 1: Cari berdasarkan text pattern
        print("🔍 Mencari harga...")
        page_source = driver.page_source

        # Cari semua elemen yang mungkin berisi harga
        potential_price_elements = driver.find_elements(
            By.XPATH, "//*[contains(text(), 'Rp') or contains(text(), '/g')]"
        )

        found_prices = []
        for element in potential_price_elements:
            try:
                text = element.text.strip()
                if text and ("Rp" in text or "/g" in text):
                    price = extract_price_from_text(text)
                    if price:
                        found_prices.append((price, text))
                        print(f"💰 Kandidat harga: {price:,.0f} dari text: '{text}'")
            except:
                continue

        # Strategi 2: Cari di specific selectors
        selectors_to_try = [
            "h5",
            "[class*='price']",
            "[class*='value']",
            "[class*='amount']",
            "span",
            "div",
        ]

        for selector in selectors_to_try:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and len(text) < 100:  # Avoid very long text
                        price = extract_price_from_text(text)
                        if price and (price, text) not in found_prices:
                            found_prices.append((price, text))
                            print(
                                f"💰 Kandidat harga dari {selector}: {price:,.0f} - '{text}'"
                            )
            except:
                continue

        # Return harga tertinggi (paling update)
        if found_prices:
            latest_price = max(found_prices, key=lambda x: x[0])
            return latest_price[0], latest_price[1]

        # Fallback: scan seluruh page source
        print("🔄 Fallback: scanning page source...")
        price = extract_price_from_text(page_source)
        if price:
            return price, "page source"

        return None, None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None
    finally:
        if driver:
            driver.quit()


def main():
    print("🏷️  Scraping Harga Emas Pluang dengan Selenium")
    print("=" * 50)

    price, source = scrape_gold_price()

    if price:
        print(f"\n✅ Harga Emas Terbaru: Rp{price:,.0f} per gram")
        print(f"📍 Sumber: {source}")
    else:
        print("\n❌ Gagal mendapatkan harga emas")
        print("💡 Tips:")
        print("   - Pastikan ChromeDriver terinstall")
        print("   - Periksa koneksi internet")
        print("   - Website mungkin memblok automated access")


if __name__ == "__main__":
    main()

# Install requirements:
# pip install selenium
# Download ChromeDriver from https://chromedriver.chromium.org/
