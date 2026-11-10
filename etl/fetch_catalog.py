import httpx
import json
import time
import os
from datetime import datetime

def fetch_all_catalog():
    os.makedirs("data", exist_ok=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }
    
    catalog = []
    page = 1
    total_count = None
    
    print("=" * 60)
    print("SIAT katalogini to'liq yuklab olish boshlandi...")
    print("=" * 60)
    
    with httpx.Client(timeout=30.0, verify=False, headers=headers) as client:
        while True:
            url = f"https://api.siat.stat.uz/sdmx/last-layer/?page={page}"
            try:
                resp = client.get(url)
                if resp.status_code != 200:
                    print(f"[Xatolik] Sahifa {page}: status {resp.status_code}")
                    break
                
                data = resp.json()
                if total_count is None:
                    total_count = data.get("count", 0)
                    print(f"Jami ko'rsatkichlar soni: {total_count}")
                
                results = data.get("results", [])
                if not results:
                    break
                
                catalog.extend(results)
                print(f"Sahifa {page} olindi. ({len(catalog)} / {total_count})")
                
                if not data.get("next"):
                    break
                
                page += 1
                time.sleep(0.5) # rate limit 1-2 req/s
            except Exception as e:
                print(f"[Xatolik] Sahifa {page} so'rovida uzilish: {e}")
                time.sleep(2)
                continue
                
    catalog_path = "data/catalog.json"
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_count": len(catalog),
            "fetched_at": datetime.now().isoformat(),
            "indicators": catalog
        }, f, ensure_ascii=False, indent=2)
        
    print("\n" + "=" * 60)
    print(f"Katalog to'liq saqlandi: {catalog_path}")
    print(f"Jami saqlangan ko'rsatkichlar: {len(catalog)} ta")
    print("=" * 60)
    return catalog

if __name__ == "__main__":
    fetch_all_catalog()
