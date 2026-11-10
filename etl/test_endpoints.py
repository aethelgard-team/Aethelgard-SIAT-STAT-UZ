import httpx
import json

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
}

endpoints = [
    "https://api.siat.stat.uz/sdmx/",
    "https://api.siat.stat.uz/sdmx/json/",
    "https://api.siat.stat.uz/sdmx/last-layer/",
    "https://api.siat.stat.uz/sdmx/search/?query=narx",
    "https://api.siat.stat.uz/sdmx/1308/",
    "https://api.siat.stat.uz/sdmx/1308/metadata/"
]

with httpx.Client(timeout=15.0, verify=False, headers=headers) as client:
    for ep in endpoints:
        try:
            r = client.get(ep)
            print(f"\nURL: {ep}")
            print(f"Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    print(f"Type: list of {len(data)} items")
                    if len(data) > 0:
                        print("First item preview:", json.dumps(data[0], ensure_ascii=False)[:200])
                elif isinstance(data, dict):
                    print(f"Type: dict with keys {list(data.keys())[:10]}")
                    print("Dict preview:", json.dumps(data, ensure_ascii=False)[:200])
        except Exception as e:
            print(f"Error {ep}: {e}")
