import httpx
import re

headers = {"User-Agent": "Mozilla/5.0"}

with httpx.Client(timeout=15.0, verify=False, headers=headers) as client:
    resp = client.get("https://siat.stat.uz/js/app.8477ab54.js")
    text = resp.text
    
    for match in re.finditer(r'.{0,100}/sdmx/.{0,100}', text):
        print("MATCH:", match.group(0))
        print("-" * 50)
