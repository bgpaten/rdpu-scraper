from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import re


def setup_driver():
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


def extract_price_from_text(text: str):
    text = re.sub(r"\s+", " ", text.strip())
    match = re.search(r"Rp\s*([0-9]{1,3}(?:\.[0-9]{3})+)", text)
    if match:
        clean_number = match.group(1).replace(".", "")
        try:
            price = float(clean_number)
            if 500000 <= price <= 10000000:  # rentang lebih fleksibel
                return price
        except ValueError:
            return None
    return None


def scrape_gold_price():
    driver = setup_driver()
    try:
        driver.get("https://pluang.com/asset/gold")

        # Tunggu body halaman ready
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Ambil semua elemen yang ada teks Rp
        elements = driver.find_elements(By.XPATH, "//*[contains(text(),'Rp')]")

        candidates = []
        print("\n🔍 Debug kandidat teks harga:")
        for el in elements:
            text = el.text.strip()
            if not text:
                continue
            if "Rp" in text and (
                "/g" in text or len(text) <= 20
            ):  # filter harga singkat
                print("➡️", text)
                price = extract_price_from_text(text)
                if price:
                    candidates.append((price, text))

        if candidates:
            # Ambil kandidat pertama yang ada /g, kalau ada
            for price, txt in candidates:
                if "/g" in txt:
                    return price, txt
            # fallback: harga valid pertama
            return candidates[0]

        return None, None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None
    finally:
        driver.quit()


def main():
    print("🏷️  Scraping Harga Emas Pluang (Debug Mode)")
    print("=" * 55)

    price, raw_text = scrape_gold_price()
    if price:
        print(f"\n✅ Harga Emas Terbaru: Rp{price:,.0f}/g")
        print(f"📍 Sumber teks: {raw_text}")
    else:
        print("\n❌ Gagal mendapatkan harga emas")


if __name__ == "__main__":
    main()
