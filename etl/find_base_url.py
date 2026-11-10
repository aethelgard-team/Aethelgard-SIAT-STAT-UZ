import httpx
import re

headers = {"User-Agent": "Mozilla/5.0"}

with httpx.Client(timeout=15.0, verify=False, headers=headers) as client:
    resp = client.get("https://siat.stat.uz/js/app.8477ab54.js")
    text = resp.text
    
    # search for axios.create or VUE_APP or api or url
    matches = re.findall(r'.{0,50}(?:axios\.create|VUE_APP_API|VUE_APP_BASE|baseUrl|baseURL).{0,50}', text)
    for m in matches:
        print("BASE MATCH:", m)
