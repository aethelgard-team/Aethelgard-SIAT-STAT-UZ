"""
=============================================================================
SIAT STAT DWH: FastAPI Complete Endpoint 200 OK Audit & Readiness Test
Loyiha: siat.stat.uz MCP Loyihasi
Muallif: Siddiq (Backend & Database Lead)
Tavsif:
  FastAPI ilovasining barcha 15 ta marshrutini (REST + SSE) 200 OK maqomi,
  javob vaqti (latensiya) va JSON/HTML tuzilmasi bo'yicha to'liq tekshirish.
  Qat'iy qoida: Emojilar mutlaqo ishlatilmaydi.
=============================================================================
"""

import sys
import os
import time
import json
from typing import Dict, Any, List

# Loyiha ildizini import yo'liga qo'shish
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# Natijalarni to'plash uchun ro'yxat
AUDIT_RESULTS: List[Dict[str, Any]] = []


def record_result(endpoint: str, method: str, status_code: int, latency_ms: float, passed: bool, note: str = ""):
    status_str = "PASS" if passed else "FAIL"
    AUDIT_RESULTS.append({
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "latency_ms": round(latency_ms, 2),
        "status": status_str,
        "note": note
    })
    print(f"[{status_str}] {method:4s} {endpoint:<45} | Status: {status_code} | Latency: {latency_ms:6.2f}ms | {note}")


def test_01_root_spa():
    t0 = time.time()
    resp = client.get("/")
    lat = (time.time() - t0) * 1000
    passed = resp.status_code == 200 and "text/html" in resp.headers.get("content-type", "") and "<!doctype html>" in resp.text.lower()
    record_result("/", "GET", resp.status_code, lat, passed, "SPA index.html muvaffaqiyatli yuklandi")
    assert passed


def test_02_health():
    t0 = time.time()
    resp = client.get("/health")
    lat = (time.time() - t0) * 1000
    data = resp.json()
    passed = resp.status_code == 200 and data.get("status") == "ok" and data.get("database_connected") is True
    record_result("/health", "GET", resp.status_code, lat, passed, "Tizim va DWH bazasi ulanishi OK")
    assert passed


def test_03_docs():
    t0 = time.time()
    resp = client.get("/docs")
    lat = (time.time() - t0) * 1000
    passed = resp.status_code == 200 and "text/html" in resp.headers.get("content-type", "")
    record_result("/docs", "GET", resp.status_code, lat, passed, "Swagger UI interfeysi mavjud")
    assert passed


def test_04_openapi_json():
    t0 = time.time()
    resp = client.get("/openapi.json")
    lat = (time.time() - t0) * 1000
    data = resp.json()
    passed = resp.status_code == 200 and "openapi" in data and "paths" in data
    record_result("/openapi.json", "GET", resp.status_code, lat, passed, f"OpenAPI sxemasi: {len(data.get('paths', {}))} ta yo'l")
    assert passed


def test_05_redoc():
    t0 = time.time()
    resp = client.get("/redoc")
    lat = (time.time() - t0) * 1000
    passed = resp.status_code == 200 and "text/html" in resp.headers.get("content-type", "")
    record_result("/redoc", "GET", resp.status_code, lat, passed, "ReDoc interfeysi mavjud")
    assert passed


def test_06_static_assets():
    t0 = time.time()
    resp = client.get("/assets/index-BMvKsoyy.css")
    lat = (time.time() - t0) * 1000
    passed = resp.status_code == 200 and len(resp.content) > 1000
    record_result("/assets/{filepath}", "GET", resp.status_code, lat, passed, f"Vite CSS aktivi yuklandi ({len(resp.content)} bayt)")
    assert passed


def test_07_api_stats():
    t0 = time.time()
    resp = client.get("/api/stats")
    lat = (time.time() - t0) * 1000
    data = resp.json()
    passed = resp.status_code == 200 and data.get("total_facts") == 2580045 and len(data.get("categories", [])) > 0
    record_result("/api/stats", "GET", resp.status_code, lat, passed, f"2.58M fakt, {data.get('total_indicators')} ko'rsatkich")
    assert passed


def test_08_indicators_search():
    t0 = time.time()
    resp = client.get("/api/indicators/search?q=mol+go'shti&lang=uz&limit=5")
    lat = (time.time() - t0) * 1000
    data = resp.json()
    results = data.get("results", [])
    passed = resp.status_code == 200 and len(results) > 0 and results[0].get("indicator_id") == 1308
    record_result("/api/indicators/search", "GET", resp.status_code, lat, passed, f"RRF qidiruvi: Top 1 ID={results[0].get('indicator_id') if results else 'none'}")
    assert passed


def test_09_indicator_metadata():
    t0 = time.time()
    resp = client.get("/api/indicators/1308")
    lat = (time.time() - t0) * 1000
    data = resp.json()
    passed = resp.status_code == 200 and data.get("indicator_id") == 1308 and "name_uz" in data
    record_result("/api/indicators/{indicator_id}", "GET", resp.status_code, lat, passed, f"Ko'rsatkich 1308: {data.get('name_uz', '')[:30]}...")
    assert passed


def test_10_series():
    t0 = time.time()
    resp = client.get("/api/series?indicator_id=1308&item_codes=017&from=2026-M01&to=2026-M09")
    lat = (time.time() - t0) * 1000
    data = resp.json()
    rows = data.get("data", [])
    passed = resp.status_code == 200 and len(rows) > 0 and abs(rows[-1].get("value", 0) - 127857.3) < 0.1
    record_result("/api/series", "GET", resp.status_code, lat, passed, f"{len(rows)} ta qator qaytdi, so'nggi qiymat: {rows[-1].get('value') if rows else 'none'}")
    assert passed


def test_11_data():
    t0 = time.time()
    resp = client.get("/api/data?indicator_id=1308&item_codes=017&periods=2026-M09&limit=10")
    lat = (time.time() - t0) * 1000
    data = resp.json()
    rows = data.get("data", [])
    passed = resp.status_code == 200 and len(rows) == 1 and abs(rows[0].get("value", 0) - 127857.3) < 0.1
    record_result("/api/data", "GET", resp.status_code, lat, passed, f"1 ta fakt: {rows[0].get('value') if rows else 'none'} so'm")
    assert passed


def test_12_periods():
    t0 = time.time()
    resp = client.get("/api/periods?indicator_id=1308")
    lat = (time.time() - t0) * 1000
    data = resp.json()
    passed = resp.status_code == 200 and "periods" in data and len(data.get("periods", [])) > 0
    record_result("/api/periods", "GET", resp.status_code, lat, passed, f"Jami {len(data.get('periods', []))} ta davr mavjud")
    assert passed


def test_13_regions_compare():
    t0 = time.time()
    resp = client.get("/api/regions/compare?indicator_id=273&period=2024")
    lat = (time.time() - t0) * 1000
    data = resp.json()
    items = data.get("ranking", [])
    passed = resp.status_code == 200 and len(items) > 0 and "republic_benchmark" in data
    record_result("/api/regions/compare", "GET", resp.status_code, lat, passed, f"{len(items)} ta hudud saralandi (Top 1: {items[0].get('region_name') if items else 'none'})")
    assert passed


def test_14_forecast():
    t0 = time.time()
    resp = client.get("/api/forecast?indicator_id=1308&target_year=2030&item_code=017")
    lat = (time.time() - t0) * 1000
    data = resp.json()
    val = data.get("predicted_value") or data.get("forecast_value")
    model = data.get("model_used") or data.get("method_used")
    passed = (
        resp.status_code == 200
        and data.get("target_year") == 2030
        and val is not None
        and isinstance(val, (int, float))
        and val > 0
        and model is not None
    )
    record_result(
        "/api/forecast",
        "GET",
        resp.status_code,
        lat,
        passed,
        f"2030 prognozi: {val} ({model})"
    )
    assert passed


def _parse_sse_stream(text: str) -> List[Dict[str, Any]]:
    events = []
    chunks = text.strip().split("\n\n")
    for chunk in chunks:
        lines = chunk.strip().split("\n")
        ev_name = None
        ev_data = None
        for line in lines:
            if line.startswith("event:"):
                ev_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                raw_json = line.split(":", 1)[1].strip()
                try:
                    ev_data = json.loads(raw_json)
                except Exception:
                    ev_data = raw_json
        if ev_name:
            events.append({"event": ev_name, "data": ev_data})
    return events


def test_15_ask_sse_stream():
    # 5 xil tipdagi so'rovlarni POST /api/ask orqali sinovdan o'tkazish
    test_queries = [
        ("Factual (O'zbek)", "2026-yil sentyabrda mol go'shtining o'rtacha narxi qancha edi?"),
        ("Russian Translation", "Какова цена говядины в сентябре 2026 года?"),
        ("Compound Query", "tuxum narxi va Toshkent aholisi nechta?"),
        ("ML Forecast (2030)", "2030-yilda mol go'shti narxi qancha bo'ladi?"),
        ("Out-of-Scope", "Bitcoin narxi qancha bo'ladi?")
    ]

    all_passed = True
    total_lat = 0.0

    for q_type, q_text in test_queries:
        t0 = time.time()
        resp = client.post(
            "/api/ask",
            json={"question": q_text},
            headers={"Accept": "text/event-stream"}
        )
        lat = (time.time() - t0) * 1000
        total_lat += lat

        is_sse = "text/event-stream" in resp.headers.get("content-type", "")
        events = _parse_sse_stream(resp.text)
        event_names = [e["event"] for e in events]
        has_done = "done" in event_names
        q_pass = resp.status_code == 200 and is_sse and has_done

        print(f"  * [SSE Subtest] {q_type:<20} | Status: {resp.status_code} | Latency: {lat:6.2f}ms | Events: {event_names}")
        if not q_pass:
            all_passed = False

    avg_lat = total_lat / len(test_queries)
    record_result(
        "/api/ask",
        "POST",
        200 if all_passed else 500,
        avg_lat,
        all_passed,
        f"5 ta SSE oqimi sinovi (Factual, Ruscha, Murakkab, ML Prognoz, Out-of-scope) - barchasida 'done' voqeasi olindi"
    )
    assert all_passed


def print_markdown_table():
    print("\n" + "=" * 90)
    print("FASTAPI AUDIT NATIJALARI (MARKDOWN JADVAL)")
    print("=" * 90)
    print("| Tartib | Endpoint | Metod | Status Code | Latensiya (ms) | Holat | Izoh |")
    print("|---|---|---|---|---|---|---|")
    for idx, r in enumerate(AUDIT_RESULTS, 1):
        print(f"| {idx} | `{r['endpoint']}` | `{r['method']}` | `{r['status_code']}` | `{r['latency_ms']:.2f}` | **{r['status']}** | {r['note']} |")
    print("=" * 90)


if __name__ == "__main__":
    print("=" * 80)
    print("FASTAPI ENDPOINTS 200 OK AUDIT SINOVI BOSHLANDI")
    print("=" * 80)

    test_01_root_spa()
    test_02_health()
    test_03_docs()
    test_04_openapi_json()
    test_05_redoc()
    test_06_static_assets()
    test_07_api_stats()
    test_08_indicators_search()
    test_09_indicator_metadata()
    test_10_series()
    test_11_data()
    test_12_periods()
    test_13_regions_compare()
    test_14_forecast()
    test_15_ask_sse_stream()

    print_markdown_table()
    print("\nBARCHA FASTAPI ENDPOINTLARI 200 OK AUDITIDAN MUVAFFAQIYATLI O'TDI.")
