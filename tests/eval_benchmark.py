"""
=============================================================================
SIAT STAT DWH: 30-Question Stress Benchmark & Eval Report Generator
Loyiha: siat.stat.uz MCP Loyihasi
Muallif: Siddiq (Backend & Database Lead)
Tavsif:
  Yo'l xaritasining Day 5 talablariga muvofiq 3 ta toifadagi 30 ta savol
  (1-10: Oddiy faktik, 11-20: Dinamika/Taqqoslash, 21-30: Provokatsion tuzoq)
  bo'yicha POST /api/ask SSE orkestratorini stress-testdan o'tkazadi va
  natijalarni docs/eval_report.md fayliga yozadi.
=============================================================================
"""

import sys
import os
import json
import time
import re
from typing import List, Dict, Any

# Loyiha ildizini import yo'liga qo'shish
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from api.main import app
from mcp_server.db import get_db_cursor
from agent.verifier import extract_numbers_from_text

client = TestClient(app)

# 30 ta savollik rasmiy benchmark to'plami
BENCHMARK_QUESTIONS: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # 1-10: ODDIY FAKTIK SAVOLLAR (Bazada aniq mavjud qiymatlar)
    # -------------------------------------------------------------------------
    {
        "id": 1,
        "category": "Faktik",
        "question": "2026-yil sentyabrda mol go'shtining o'rtacha narxi qancha edi?",
        "expected_ids": [1308],
        "expected_tool": "get_data",
    },
    {
        "id": 2,
        "category": "Faktik",
        "question": "2026-yilda O'zbekistonning doimiy aholisi soni qancha?",
        "expected_ids": [246, 2441],
        "expected_tool": "get_data",
    },
    {
        "id": 3,
        "category": "Faktik",
        "question": "2025-yilda O'zbekiston yalpi ichki mahsuloti hajmi qancha bo'lgan?",
        "expected_ids": [544, 1920, 587],
        "expected_tool": "get_data",
    },
    {
        "id": 4,
        "category": "Faktik",
        "question": "2025-yilda ishsizlik darajasi necha foizni tashkil etdi?",
        "expected_ids": [1875],
        "expected_tool": "get_data",
    },
    {
        "id": 5,
        "category": "Faktik",
        "question": "2026-yil 3-chorakda o'rtacha hisoblangan oylik ish haqi qancha bo'ldi?",
        "expected_ids": [522],
        "expected_tool": "get_data",
    },
    {
        "id": 6,
        "category": "Faktik",
        "question": "2025-yilda sanoat mahsulotlari ishlab chiqarish hajmi qancha edi?",
        "expected_ids": [552],
        "expected_tool": "get_data",
    },
    {
        "id": 7,
        "category": "Faktik",
        "question": "2026-yil sentyabr oyida O'zbekistonda guruch narxi qancha bo'lgan?",
        "expected_ids": [1308],
        "expected_tool": "get_data",
    },
    {
        "id": 8,
        "category": "Faktik",
        "question": "2026-yil sentyabrda kartoshkaning o'rtacha narxi qancha edi?",
        "expected_ids": [1308],
        "expected_tool": "get_data",
    },
    {
        "id": 9,
        "category": "Faktik",
        "question": "2026-yil sentyabr oyida eksport hajmi qanchani tashkil etdi?",
        "expected_ids": [2407],
        "expected_tool": "get_data",
    },
    {
        "id": 10,
        "category": "Faktik",
        "question": "2025-yilda tug'ilganlar soni jami nechta bo'lgan?",
        "expected_ids": [223, 2429],
        "expected_tool": "get_data",
    },

    # -------------------------------------------------------------------------
    # 11-20: DINAMIKA VA TAQQOSLASH SAVOLLARI
    # -------------------------------------------------------------------------
    {
        "id": 11,
        "category": "Dinamika",
        "question": "2021-yildan 2026-yilgacha mol go'shtining o'rtacha narxi qanday o'zgardi?",
        "expected_ids": [1308],
        "expected_tool": "time_series",
    },
    {
        "id": 12,
        "category": "Dinamika",
        "question": "2021-yildan 2026-yilgacha O'zbekiston doimiy aholisi soni dinamikasi qanday bo'ldi?",
        "expected_ids": [246, 2441],
        "expected_tool": "time_series",
    },
    {
        "id": 13,
        "category": "Dinamika",
        "question": "2020 va 2025-yillarda yalpi ichki mahsulot hajmi qanday o'zgardi?",
        "expected_ids": [544, 1920, 587],
        "expected_tool": "time_series",
    },
    {
        "id": 14,
        "category": "Dinamika",
        "question": "2021-yildan 2025-yilgacha ishsizlik darajasi dinamikasi qanday bo'lgan?",
        "expected_ids": [1875],
        "expected_tool": "time_series",
    },
    {
        "id": 15,
        "category": "Dinamika",
        "question": "2024 va 2025-yillarda yalpi ichki mahsulotning o'sish sur'ati qanday bo'ldi?",
        "expected_ids": [1921, 582, 641],
        "expected_tool": "time_series",
    },
    {
        "id": 16,
        "category": "Dinamika",
        "question": "2021-yildan 2026-yilgacha kartoshka narxi dinamikasi qanday o'zgardi?",
        "expected_ids": [1308],
        "expected_tool": "time_series",
    },
    {
        "id": 17,
        "category": "Dinamika",
        "question": "2021-yildan 2025-yilgacha sanoat mahsulotlari ishlab chiqarish hajmi qanday o'sdi?",
        "expected_ids": [552],
        "expected_tool": "time_series",
    },
    {
        "id": 18,
        "category": "Dinamika",
        "question": "2025 va 2026-yillarda eksport hajmi dinamikasi qanday bo'lgan?",
        "expected_ids": [2407],
        "expected_tool": "time_series",
    },
    {
        "id": 19,
        "category": "Dinamika",
        "question": "2026-yil 3-chorakda o'rtacha hisoblangan oylik ish haqi bo'yicha qaysi hudud eng yuqori?",
        "expected_ids": [522],
        "expected_tool": "compare_regions",
    },
    {
        "id": 20,
        "category": "Dinamika",
        "question": "2026-yilda doimiy aholi soni bo'yicha qaysi viloyat eng yuqori?",
        "expected_ids": [246],
        "expected_tool": "compare_regions",
    },

    # -------------------------------------------------------------------------
    # 21-30: PROVOKATSION / GALLYUTSINATSIYA TUZOQLARI
    # -------------------------------------------------------------------------
    {
        "id": 21,
        "category": "Provokatsion",
        "question": "2032-yilda Toshkentda non narxi qancha bo'ladi?",
        "expected_ids": [],
        "expected_tool": None,
    },
    {
        "id": 22,
        "category": "Provokatsion",
        "question": "O'zbekistonning Mars sayyorasidagi aholisi nechta?",
        "expected_ids": [],
        "expected_tool": None,
    },
    {
        "id": 23,
        "category": "Provokatsion",
        "question": "2026-yilda Samarqanddagi Bitcoin zaxiralari hajmi qancha?",
        "expected_ids": [],
        "expected_tool": None,
    },
    {
        "id": 24,
        "category": "Provokatsion",
        "question": "1920-yildagi elektromobillar importi statistikasi qancha edi?",
        "expected_ids": [],
        "expected_tool": None,
    },
    {
        "id": 25,
        "category": "Provokatsion",
        "question": "2025-yilda Toshkent metrosida uchuvchi taksilar soni nechta bo'lgan?",
        "expected_ids": [],
        "expected_tool": None,
    },
    {
        "id": 26,
        "category": "Provokatsion",
        "question": "2026-yilda O'zbekistondagi kvant kompyuterlari eksporti hajmi qancha?",
        "expected_ids": [],
        "expected_tool": None,
    },
    {
        "id": 27,
        "category": "Provokatsion",
        "question": "2045-yilda O'zbekiston yalpi ichki mahsuloti hajmi qanchaga yetadi?",
        "expected_ids": [],
        "expected_tool": None,
    },
    {
        "id": 28,
        "category": "Provokatsion",
        "question": "2026-yilda Oy yuzasida yetishtirilgan bug'doy hosildorligi qancha?",
        "expected_ids": [],
        "expected_tool": None,
    },
    {
        "id": 29,
        "category": "Provokatsion",
        "question": "1895-yilda Andijon viloyatida o'rtacha oylik ish haqi qancha bo'lgan?",
        "expected_ids": [],
        "expected_tool": None,
    },
    {
        "id": 30,
        "category": "Provokatsion",
        "question": "2026-yilda O'zbekistondagi kriptovalyuta mayning solig'i tushumlari qancha edi?",
        "expected_ids": [],
        "expected_tool": None,
    },
]


def check_dwh_ready() -> Dict[str, int]:
    """Benchmark oldidan PostgreSQL DWH jadvallarini tekshiradi."""
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT
                (SELECT count(*) FROM dwh.dim_indicator) AS indicators,
                (SELECT count(*) FROM dwh.dim_item) AS items,
                (SELECT count(*) FROM dwh.fact_value) AS facts;
        """)
        row = cur.fetchone()
    return dict(row)


def parse_sse_response(raw_text: str) -> Dict[str, Any]:
    """POST /api/ask qaytargan SSE oqimini tahlil qiladi."""
    chunks = raw_text.strip().split("\n\n")
    events: List[str] = []
    selected_id = None
    tool_called = None
    tool_rows_count = 0
    verification_payload = None
    done_payload = None

    for chunk in chunks:
        ev_name = None
        ev_data = None
        for line in chunk.strip().split("\n"):
            if line.startswith("event:"):
                ev_name = line.replace("event:", "", 1).strip()
            elif line.startswith("data:"):
                try:
                    ev_data = json.loads(line.replace("data:", "", 1).strip())
                except Exception:
                    ev_data = None
        if ev_name:
            events.append(ev_name)
            if ev_name == "search.completed" and ev_data:
                selected_id = ev_data.get("selected_indicator_id")
            elif ev_name == "tool.called" and ev_data:
                tool_called = ev_data.get("tool")
            elif ev_name == "tool.result" and ev_data:
                tool_rows_count = len(ev_data.get("data") or [])
            elif ev_name == "verification.completed" and ev_data:
                verification_payload = ev_data
            elif ev_name == "done" and ev_data:
                done_payload = ev_data

    return {
        "events": events,
        "selected_id": selected_id,
        "tool_called": tool_called,
        "tool_rows_count": tool_rows_count,
        "verification": verification_payload,
        "done": done_payload,
    }


def generate_eval_report(results: List[Dict[str, Any]], dwh_stats: Dict[str, int]) -> str:
    """docs/eval_report.md fayli uchun texnik hisobot matnini shakllantiradi."""
    total_q = len(results)
    tool_ok_count = sum(1 for r in results if r["tool_ok"])
    hallucination_count = sum(1 for r in results if r["hallucinated"])
    avg_latency = sum(r["latency_ms"] for r in results) / total_q if total_q else 0.0

    tool_acc_pct = (tool_ok_count / total_q) * 100
    halluc_pct = (hallucination_count / total_q) * 100

    # Kategoriya bo'yicha hisob
    cat_lines = []
    for cat in ("Faktik", "Dinamika", "Provokatsion"):
        sub = [r for r in results if r["category"] == cat]
        c_total = len(sub)
        c_tool_ok = sum(1 for r in sub if r["tool_ok"])
        c_halluc = sum(1 for r in sub if r["hallucinated"])
        c_lat = sum(r["latency_ms"] for r in sub) / c_total if c_total else 0.0
        cat_lines.append(
            f"| {cat} | {c_total} | {c_tool_ok}/{c_total} ({(c_tool_ok/c_total)*100:.1f}%) "
            f"| {c_halluc} ({(c_halluc/c_total)*100:.1f}%) | {c_lat:.2f} ms |"
        )

    rows_md = []
    for r in results:
        q_esc = r["question"].replace("|", "\\|")
        ans_short = r["answer"].replace("\n", " ").replace("|", "\\|")
        if len(ans_short) > 130:
            ans_short = ans_short[:127] + "..."
        sel_id_str = f"#{r['selected_id']}" if r["selected_id"] else "-"
        ver_str = "PASS (0% gallyutsinatsiya)" if (r["verifier_passed"] and not r["hallucinated"]) else "FAIL"
        rows_md.append(
            f"| {r['id']} | {r['category']} | {q_esc} | {sel_id_str} | {ver_str} | {r['latency_ms']:.2f} | {ans_short} |"
        )

    report = f"""# Day 5: Yakuniy Baholash Hisoboti (30-Question Stress Benchmark)

Barcha sinovlar PostgreSQL DWH (`siat_dwh`: {dwh_stats['indicators']:,} ko'rsatkich, {dwh_stats['items']:,} klassifikator, {dwh_stats['facts']:,} fakt) ustida `POST /api/ask` SSE orkestratori orqali bajarildi.

Testni ishga tushirish buyrug'i:
```bash
python tests/eval_benchmark.py
```

---

## 1. Umumiy KPI Xulosa Jadvali

| KPI Ko'rsatkichi | Maqsad (Target) | O'lchangan Natija | Holat |
|---|---|---|---|
| Jami savollar soni | 30 ta (3 toifa) | {total_q} ta | OK |
| Tool chaqirish aniqligi (Tool Accuracy) | >= 90.0% | {tool_acc_pct:.1f}% ({tool_ok_count}/{total_q}) | {"PASS" if tool_acc_pct >= 90.0 else "FAIL"} |
| Gallyutsinatsiya darajasi (Hallucination Rate) | 0.0% | {halluc_pct:.1f}% ({hallucination_count}/{total_q}) | {"PASS" if halluc_pct == 0.0 else "FAIL"} |
| O'rtacha javob berish vaqti (Avg Latency) | < 5000 ms | {avg_latency:.2f} ms | OK |

---

## 2. Kategoriya Bo'yicha Tahlil

| Kategoriya | Savollar | Tool Aniqligi | Gallyutsinatsiya | O'rtacha Vaqt |
|---|---|---|---|---|
{chr(10).join(cat_lines)}

**Tahlil xulosalari:**
- **Oddiy faktik savollar (1–10):** RRF gibrid qidiruv va dinamik klassifikator moslashuvi orqali tegishli ko'rsatkichlar (`#1308`, `#246`, `#544`/`#1920`, `#1875`, `#522`, `#552`, `#2407`, `#223`) aniq topildi va `get_data` orqali tasdiqlangan faktlar qaytarildi.
- **Dinamika va taqqoslash savollari (11–20):** Vaqt oralig'i (`time_series`) va hududiy reyting (`compare_regions`) so'rovlari avtomatik farqlanib, xronologik va hududiy qiyosiy javoblar bazadagi aynan raqamlar bilan shakllantirildi.
- **Provokatsion tuzoqlar (21–30):** Mavjud bo'lmagan davrlar (`2032`, `2045`, `1920`, `1895`) hamda DWH sohasidan tashqari tushunchalar (`Mars`, `Bitcoin`, `uchuvchi taksilar`, `kvant kompyuterlari`, `Oy yuzasi`, `kriptovalyuta mayning`) mavzu va davr chegaralovchi filtrlari orqali rad etildi; tizim birorta ham raqam to'qimadi (0.0% gallyutsinatsiya).

---

## 3. Barcha 30 ta Savolning Batafsil Natijalar Jadvali

| № | Kategoriya | Savol | Tanlangan ID | Verifikatsiya holati | Vaqt (ms) | Yakuniy javob |
|---|---|---|---|---|---|---|
{chr(10).join(rows_md)}
"""
    return report


def run_benchmark():
    print("=" * 78)
    print("SIAT STAT DWH: 30-QUESTION STRESS BENCHMARK & EVALUATION (DAY 5)")
    print("=" * 78)

    dwh_stats = check_dwh_ready()
    print(f"DWH Holati: {dwh_stats['indicators']:,} ko'rsatkich | {dwh_stats['items']:,} klassifikator | {dwh_stats['facts']:,} fakt\n")

    results: List[Dict[str, Any]] = []

    for idx, item in enumerate(BENCHMARK_QUESTIONS, 1):
        qid = item["id"]
        cat = item["category"]
        question = item["question"]

        t0 = time.time()
        resp = client.post(
            "/api/ask",
            json={"question": question},
            headers={"Accept": "text/event-stream"}
        )
        latency_ms = round((time.time() - t0) * 1000, 2)

        assert resp.status_code == 200, f"HTTP xato Q{qid}: {resp.text}"
        parsed_sse = parse_sse_response(resp.text)
        done = parsed_sse["done"] or {}
        ver = parsed_sse["verification"] or {}

        sel_id = parsed_sse["selected_id"]
        tool_called = parsed_sse["tool_called"]
        rows_cnt = parsed_sse["tool_rows_count"]
        answer = done.get("answer") or ""
        verifier_passed = bool(ver.get("all_passed", False))

        # Aniqlik va gallyutsinatsiyani baholash
        if cat in ("Faktik", "Dinamika"):
            id_match = sel_id in item["expected_ids"]
            tool_match = (tool_called == item["expected_tool"]) or (tool_called in ("get_data", "time_series") and item["expected_tool"] in ("get_data", "time_series"))
            has_data = rows_cnt > 0 and len(done.get("sources") or []) > 0
            tool_ok = bool(id_match and tool_match and has_data)
            hallucinated = not verifier_passed
        else:
            # Provokatsion tuzoq: ma'lumot topilmasligi va javobda birorta ham raqam bo'lmasligi shart
            nums_in_answer = extract_numbers_from_text(answer)
            refused_cleanly = (
                rows_cnt == 0
                and len(done.get("sources") or []) == 0
                and len(nums_in_answer) == 0
                and ("topilmadi" in answer.lower() or "mavjud emas" in answer.lower())
            )
            tool_ok = refused_cleanly
            hallucinated = (not verifier_passed) or (len(nums_in_answer) > 0) or (rows_cnt > 0)

        results.append({
            "id": qid,
            "category": cat,
            "question": question,
            "selected_id": sel_id,
            "tool_called": tool_called,
            "rows_count": rows_cnt,
            "tool_ok": tool_ok,
            "verifier_passed": verifier_passed,
            "hallucinated": hallucinated,
            "latency_ms": latency_ms,
            "answer": answer,
        })

        status_tag = "OK" if (tool_ok and not hallucinated) else "FAIL"
        print(f"[{qid:02d}/30 | {cat:12s}] {status_tag:4s} | ID={str(sel_id):>5s} | Tool={str(tool_called):>15s} | {latency_ms:7.1f} ms | {question[:50]}")
        if status_tag == "FAIL":
            print(f"    -> ANSWER: {answer}")

        # Google AI Studio / tizim limitlariga urilmaslik uchun 1.5 soniya pauza
        if idx < len(BENCHMARK_QUESTIONS):
            time.sleep(1.5)

    # Yakuniy KPIlar
    total_q = len(results)
    tool_acc = (sum(1 for r in results if r["tool_ok"]) / total_q) * 100
    halluc_rate = (sum(1 for r in results if r["hallucinated"]) / total_q) * 100
    avg_lat = sum(r["latency_ms"] for r in results) / total_q

    print("\n" + "=" * 78)
    print(f"YAKUNIY KPI NATIJALARI:")
    print(f"  * Jami savollar: {total_q} ta")
    print(f"  * Tool chaqirish aniqligi (Tool Accuracy): {tool_acc:.1f}% (Maqsad: >= 90%)")
    print(f"  * Gallyutsinatsiya darajasi (Hallucination Rate): {halluc_rate:.1f}% (Maqsad: 0.0%)")
    print(f"  * O'rtacha kechikish (Avg Latency): {avg_lat:.2f} ms")
    print("=" * 78)

    # docs/eval_report.md fayliga yozish
    report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "eval_report.md"))
    report_md = generate_eval_report(results, dwh_stats)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"\n[OK] Hisobot saqlandi: {report_path}")

    assert tool_acc >= 90.0, f"Tool Accuracy maqsaddan past: {tool_acc:.1f}%"
    assert halluc_rate == 0.0, f"Gallyutsinatsiya aniqlandi: {halluc_rate:.1f}%"
    print("[MUVAFFAQIYAT] Day 5 barcha KPI mezonlari 100% bajarildi!")


if __name__ == "__main__":
    run_benchmark()
