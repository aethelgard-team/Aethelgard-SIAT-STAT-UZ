import httpx
import re
import json

def discover():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    with httpx.Client(timeout=15.0, verify=False, headers=headers) as client:
        print("[1] Fetching https://siat.stat.uz ...")
        resp = client.get("https://siat.stat.uz")
        print(f"Status: {resp.status_code}, Length: {len(resp.text)}")
        
        # Find script tags
        scripts = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', resp.text)
        print(f"Found {len(scripts)} scripts: {scripts}")
        
        api_patterns = set()
        for s in scripts:
            if not s.startswith("http"):
                script_url = "https://siat.stat.uz" + ("/" if not s.startswith("/") else "") + s
            else:
                script_url = s
            print(f"\n[2] Inspecting script: {script_url}")
            try:
                s_resp = client.get(script_url)
                if s_resp.status_code == 200:
                    text = s_resp.text
                    # Search for urls / endpoints
                    matches = re.findall(r'(https?://api\.siat\.stat\.uz[^\s"\'`)]+|/api/[a-zA-Z0-9_\-/]+)', text)
                    for m in set(matches):
                        api_patterns.add(m)
            except Exception as e:
                print(f"Error fetching script: {e}")
                
        print("\n" + "="*50)
        print("Discovered API endpoints / paths:")
        for ep in sorted(api_patterns):
            print("  *", ep)
        print("="*50)

if __name__ == "__main__":
    discover()
