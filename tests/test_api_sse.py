"""
=============================================================================
SIAT STAT DWH: FastAPI and SSE Integration Test Suite (tests/test_api_sse.py)
Loyiha: siat.stat.uz MCP Loyihasi
Muallif: Siddiq (Backend & Database Lead)
Tavsif:
  FastAPI serveri endpointlarini va POST /api/ask SSE oqimini avtomatlashtirilgan
  tarzda sinovdan o'tkazish.
  Roadmap talabi: "Mol go'shti, 2026-M09" savoli bo'yicha barcha 7 ta SSE
  bosqichlari va 127 857.3 qiymatining verifikatsiyasini tekshiradi.
=============================================================================
"""

import sys
import os
import json
import time

# Loyiha ildizini import yo'liga qo'shish
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_rest_endpoints():
    print("=" * 75)
    print("1-QISM: REST API ENDPOINTLARI SINOVI")
    print("=" * 75)

    # 1. GET /health
    print("\n[REST 1/4] GET /health tekshiruvi...")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health xatosi: {resp.text}"
    health_data = resp.json()
    print("  * Status:", health_data["status"])
    print("  * Baza ulanishi:", health_data["database_connected"])
    assert health_data["status"] == "ok"
    assert health_data["database_connected"] is True
    print("  -> [OK] Health endpointi muvaffaqiyatli o'tdi.")

    # 2. GET /api/stats
    print("\n[REST 2/4] GET /api/stats tekshiruvi...")
    resp = client.get("/api/stats")
    assert resp.status_code == 200, f"Stats xatosi: {resp.text}"
    stats_data = resp.json()
    print(f"  * Jami ko'rsatkichlar: {stats_data['total_indicators']:,} ta")
    print(f"  * Jami klassifikatorlar: {stats_data['total_items']:,} ta")
    print(f"  * Jami faktlar: {stats_data['total_facts']:,} qator")
    assert stats_data["total_facts"] == 2580045, "Faktlar soni mos kelmadi!"
    print("  -> [OK] Stats endpointi muvaffaqiyatli o'tdi.")

    # 3. GET /api/indicators/search
    print("\n[REST 3/4] GET /api/indicators/search?q=mol+goshti tekshiruvi...")
    resp = client.get("/api/indicators/search?q=mol+goshti&limit=3")
    assert resp.status_code == 200, f"Search xatosi: {resp.text}"
    search_data = resp.json()
    print(f"  * Topilgan natijalar: {search_data['count']} ta")
    top_hit = search_data["results"][0]
    print(f"  * 1-natija: #{top_hit['indicator_id']} - {top_hit['name_uz']}")
    assert top_hit["indicator_id"] == 1308
    print("  -> [OK] Search endpointi muvaffaqiyatli o'tdi.")

    # 4. GET /api/series
    print("\n[REST 4/4] GET /api/series tekshiruvi (Mol go'shti, 2026-M09)...")
    resp = client.get("/api/series?indicator_id=1308&item_codes=017&from=2026-M09&to=2026-M09")
    assert resp.status_code == 200, f"Series xatosi: {resp.text}"
    series_data = resp.json()
    assert series_data["total_returned"] == 1
    row = series_data["data"][0]
    val = row["value"]
    print(f"  * Mahsulot: {row['item_name']} | Qiymat: {val} so'm | Status: {row['status']}")
    assert abs(val - 127857.3) < 0.01
    print("  -> [OK] Series endpointi muvaffaqiyatli o'tdi.")


def test_sse_ask_orchestrator():
    print("\n" + "=" * 75)
    print("2-QISM: POST /api/ask SSE ORKESTRATSIYASI VA VERIFIKATSIYASI")
    print("=" * 75)

    question = "2026-yil sentyabrda mol go'shtining o'rtacha narxi qancha edi?"
    print(f"\nSavol yuborilmoqda: '{question}'...")

    t0 = time.time()
    response = client.post(
        "/api/ask",
        json={"question": question},
        headers={"Accept": "text/event-stream"}
    )
    dur_total = (time.time() - t0) * 1000

    assert response.status_code == 200, f"SSE xatosi: {response.text}"
    assert "text/event-stream" in response.headers.get("content-type", "")

    # SSE bloklarini ajratish
    chunks = response.text.strip().split("\n\n")
    print(f"  * Olingan SSE xabarlari soni: {len(chunks)} ta")
    print(f"  * Umumiy oqim vaqti: {dur_total:.2f} ms")

    events_seen = []
    done_payload = None
    verification_payload = None
    tool_result_payload = None

    for chunk in chunks:
        lines = chunk.strip().split("\n")
        event_name = None
        data_json = None
        for line in lines:
            if line.startswith("event:"):
                event_name = line.replace("event:", "").strip()
            elif line.startswith("data:"):
                data_str = line.replace("data:", "").strip()
                try:
                    data_json = json.loads(data_str)
                except Exception:
                    pass

        if event_name:
            events_seen.append(event_name)
            if event_name == "done":
                done_payload = data_json
            elif event_name == "verification.completed":
                verification_payload = data_json
            elif event_name == "tool.result":
                tool_result_payload = data_json

    print("\n  -> Kuzatilgan SSE voqealari ro'yxati:")
    unique_events = []
    for ev in events_seen:
        if not unique_events or unique_events[-1] != ev:
            unique_events.append(ev)
    for idx, u_ev in enumerate(unique_events, 1):
        print(f"     {idx}. {u_ev}")

    # Barcha 7 bosqich borligini tekshirish
    required_events = [
        "stage.started",
        "stage.completed",
        "search.completed",
        "tool.called",
        "tool.result",
        "generation.delta",
        "verification.completed",
        "done"
    ]
    for req_ev in required_events:
        assert req_ev in events_seen, f"Kutilgan '{req_ev}' SSE voqeasi oqimda topilmadi!"

    # Natija va Verifikatsiya tekshiruvlari
    assert tool_result_payload is not None, "tool.result ma'lumotlari kelmadi!"
    print(f"\n  * Tool natijasidagi qatorlar: {len(tool_result_payload.get('data', []))} ta")

    assert verification_payload is not None, "verification.completed ma'lumotlari kelmadi!"
    print(f"  * Nol-gallyutsinatsiya verifikatsiyasi: all_passed = {verification_payload.get('all_passed')}")
    print(f"  * Checklist: {verification_payload.get('checklist')}")
    assert verification_payload.get("all_passed") is True, "Verifikatsiyada xatolik topildi!"

    assert done_payload is not None, "done voqeasi yakuniy javob bermadi!"
    print(f"\n  * Yakuniy javob: \"{done_payload['answer']}\"")
    print(f"  * Manbalar: {done_payload['sources']}")

    # 127 857.3 qiymati javobda yoki faktda borligini tekshirish
    assert "127" in done_payload["answer"] and "857" in done_payload["answer"], "127 857.3 qiymati javobda chiqmadi!"
    assert len(done_payload["sources"]) > 0, "Manbalar ko'rsatilmadi!"

    print("\n" + "=" * 75)
    print("MUVAFFAQINT: DAY 4 BARCHA INTEGRATSIYA TESTLARI 100% O'TDI!")
    print("=" * 75)


if __name__ == "__main__":
    test_rest_endpoints()
    test_sse_ask_orchestrator()
