import json

with open("data/raw/2026-11-11/sdmx_data_2943.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("Type of root:", type(data))
if isinstance(data, list) and len(data) > 0:
    first = data[0]
    print("Keys in first element:", list(first.keys()))
    print("\nMetadata sample:")
    print(json.dumps(first.get("metadata", [])[:3], indent=2, ensure_ascii=False))
    print("\nData sample (first row):")
    print(json.dumps(first.get("data", [])[:1], indent=2, ensure_ascii=False))
