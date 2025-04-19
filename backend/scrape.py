from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json
import time

def scrape_ollama_models():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    print("[*] Loading https://ollama.com/library")
    driver.get("https://ollama.com/library")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "text-xl"))
        )
    except:
        print("[!] Could not load model cards.")
        driver.quit()
        return

    cards = driver.find_elements(By.CSS_SELECTOR, "a[href^='/library/']")
    models = []
    seen = set()

    for card in cards:
        try:
            href = card.get_attribute("href")
            if not href or href in seen:
                continue
            seen.add(href)

            name = card.find_element(By.CLASS_NAME, "text-xl").text.strip()
            desc_elem = card.find_element(By.TAG_NAME, "p")
            description = desc_elem.text.strip() if desc_elem else ""

            models.append({
                "name": name,
                "description": description,
                "url": href if href.startswith("http") else "https://ollama.com" + href,
                "variants": []
            })

        except Exception:
            continue

    print(f"[*] Found {len(models)} models\n")
    driver.quit()

    with open("ollama_models.json", "w", encoding="utf-8") as f:
        json.dump(models, f, indent=2, ensure_ascii=False)

    print(f"\n[✓] Saved {len(models)} models to 'ollama_models.json'")

if __name__ == "__main__":
    scrape_ollama_models()
