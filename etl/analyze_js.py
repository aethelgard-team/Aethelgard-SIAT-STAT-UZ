import httpx
import re

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
}

with httpx.Client(timeout=15.0, verify=False, headers=headers) as client:
    resp = client.get("https://siat.stat.uz/js/app.8477ab54.js")
    text = resp.text
    print(f"app.js size: {len(text)} bytes")
    
    # Look for axios / api calls or routes
    # search for strings like "api/" or "/media/" or baseUrl or sdmx
    urls = re.findall(r'["\'](/[^"\']+)["\']', text)
    api_routes = [u for u in set(urls) if any(k in u for k in ['api', 'data', 'sdmx', 'indicator', 'catalog', 'category', 'tree', 'upload', 'media'])]
    print("Potential API routes found in app.js:")
    for r in sorted(api_routes):
        print("  -", r)

    # Let's also look for axios configuration or baseURL
    base_urls = re.findall(r'baseURL\s*:\s*["\']([^"\']+)["\']', text)
    print("baseURL settings:", base_urls)
