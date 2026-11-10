import os
import sys
import json
import time
import hashlib
import csv
from datetime import datetime
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
}

def get_target_dir():
    today = datetime.now().strftime("%Y-%m-%d")
    target_dir = os.path.join("data", "raw", today)
    os.makedirs(target_dir, exist_ok=True)
    return target_dir

def init_manifest(manifest_path):
    if not os.path.exists(manifest_path):
        with open(manifest_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "status", "size_bytes", "sha256", "download_time"])

def load_manifest(manifest_path):
    downloaded = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    downloaded[int(row["id"])] = {
                        "status": int(row["status"]),
                        "size": int(row["size_bytes"])
                    }
                except (ValueError, KeyError):
                    continue
    return downloaded

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    reraise=True
)
def fetch_sdmx_file(client, indicator_id):
    url = f"https://api.siat.stat.uz/media/uploads/sdmx/sdmx_data_{indicator_id}.json"
    resp = client.get(url)
    return resp

def extract(limit=None):
    catalog_path = "data/catalog.json"
    if not os.path.exists(catalog_path):
        print(f"[XATO] {catalog_path} topilmadi. Avval etl/fetch_catalog.py ni ishga tushiring.")
        return

    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog_data = json.load(f)

    indicators = catalog_data.get("indicators", [])
    total_indicators = len(indicators)
    print(f"Katalogda jami {total_indicators} ta ko'rsatkich bor.")

    if limit:
        indicators = indicators[:limit]
        print(f"Test rejimida dastlabki {limit} ta yuklanadi.")

    target_dir = get_target_dir()
    manifest_path = os.path.join("data", "raw", "manifest.csv")
    init_manifest(manifest_path)
    downloaded_map = load_manifest(manifest_path)

    print(f"Fayllar saqlanadigan joy: {target_dir}")
    print(f"Manifest fayl: {manifest_path}")
    print(f"Allaqachon yuklanganlar soni: {len(downloaded_map)}")
    print("=" * 60)

    success_count = 0
    fail_count = 0
    skipped_count = 0

    with httpx.Client(timeout=30.0, verify=False, headers=HEADERS) as client:
        with open(manifest_path, "a", newline="", encoding="utf-8") as mf:
            writer = csv.writer(mf)

            for idx, ind in enumerate(indicators, 1):
                ind_id = ind["id"]

                # Tekshirish: agar avval muvaffaqiyatli yuklangan bo'lsa va diskda bo'lsa
                file_path = os.path.join(target_dir, f"sdmx_data_{ind_id}.json")
                if ind_id in downloaded_map and downloaded_map[ind_id]["status"] == 200 and os.path.exists(file_path):
                    skipped_count += 1
                    continue

                status = 0
                size = 0
                sha256 = ""
                now_str = datetime.now().isoformat()

                try:
                    resp = fetch_sdmx_file(client, ind_id)
                    status = resp.status_code

                    if status == 200:
                        content = resp.content
                        size = len(content)
                        sha256 = hashlib.sha256(content).hexdigest()

                        with open(file_path, "wb") as f_out:
                            f_out.write(content)

                        success_count += 1
                        if success_count % 10 == 0 or idx == len(indicators):
                            print(f"[{idx}/{len(indicators)}] ID {ind_id} yuklandi ({size} bayt)")
                    else:
                        fail_count += 1
                        print(f"[{idx}/{len(indicators)}] ID {ind_id}: HTTP {status}")

                except Exception as e:
                    status = 599 # ichki xato / timeout
                    fail_count += 1
                    print(f"[{idx}/{len(indicators)}] ID {ind_id} xatolik: {e}")

                writer.writerow([ind_id, status, size, sha256, now_str])
                mf.flush()

                # Rate limit: 1-2 so'rov/sekund (0.6 soniya tanaffus)
                time.sleep(0.6)

    print("\n" + "=" * 60)
    print("YUKLASH YAKUNLANDI:")
    print(f"  * Muvaffaqiyatli yuklandi: {success_count}")
    print(f"  * Xatolar / 404: {fail_count}")
    print(f"  * O'tkazib yuborildi (avval bor edi): {skipped_count}")
    print("=" * 60)

if __name__ == "__main__":
    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    extract(limit=limit_arg)
