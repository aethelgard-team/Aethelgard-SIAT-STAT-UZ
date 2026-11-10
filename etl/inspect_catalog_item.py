import httpx
import json

headers = {"User-Agent": "Mozilla/5.0"}
with httpx.Client(timeout=15.0, verify=False, headers=headers) as client:
    r = client.get("https://api.siat.stat.uz/sdmx/last-layer/")
    data = r.json()
    print("Total count:", data["count"])
    print("Page items:", len(data["results"]))
    print("Sample item 0:")
    print(json.dumps(data["results"][0], indent=2, ensure_ascii=False))
    print("Sample item 1:")
    print(json.dumps(data["results"][1], indent=2, ensure_ascii=False))
