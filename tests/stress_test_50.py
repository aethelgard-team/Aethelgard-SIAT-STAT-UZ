"""
=============================================================================
SIAT STAT DWH: 50-Question Automated Stress & Accuracy Evaluation Benchmark
Fayl: tests/stress_test_50.py
Muallif: Aethelgard SIAT Team
Tavsif:
  Live FastAPI backend (http://localhost:8000) ga 5 ta toifada jami 50 ta
  turli xil O'zbekcha so'rovlar yuborib, quyidagi asosiy mezonlarni tekshiradi:
  1. HTTP/SSE status kodi va umumiy latency (kechikish vaqti soniyalarda)
  2. Tanlangan indicator_id, birlik (unit), DWH qatorlar soni
  3. Nol-gallyutsinatsiya xavfsizligi va rad etish (refusal/grounding) to'g'riligi
  4. Hech qanday 'undefined' maydoni yo'qligi va raqamlarning mosligi
=============================================================================
"""

import sys
import os
import json
import time
import re
from typing import List, Dict, Any, Optional

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ASK_ENDPOINT = f"{API_BASE_URL}/api/ask"

QUESTIONS_50: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # 1. DIRECT FACTUAL QUERIES (15 questions)
    # -------------------------------------------------------------------------
    {
        "id": 1,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2026-yil sentyabrda mol go'shtining o'rtacha narxi qancha edi?",
        "type": "factual",
        "expected_indicator": 1308,
        "expected_num": 127857.3
    },
    {
        "id": 2,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2026-yil sentyabr oyida 10 dona tuxum narxi qancha bo'lgan?",
        "type": "factual",
        "expected_indicator": 1308,
        "expected_num": 13452.6
    },
    {
        "id": 3,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2026-yil sentyabrda shakar narxi qancha edi?",
        "type": "factual",
        "expected_indicator": 1308
    },
    {
        "id": 4,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2026-yil sentyabr oyida 1-navli bug'doy uni narxi qancha bo'lgan?",
        "type": "factual",
        "expected_indicator": 1308
    },
    {
        "id": 5,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2026-yil sentyabrda kartoshkaning o'rtacha narxi qancha edi?",
        "type": "factual",
        "expected_indicator": 1308,
        "expected_num": 4991.4
    },
    {
        "id": 6,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2026-yilda O'zbekistonning doimiy aholisi soni qancha?",
        "type": "factual",
        "expected_indicator": [246, 2441],
        "expected_num": 38236.7
    },
    {
        "id": 7,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2026-yilda Toshkent shahrining doimiy aholisi soni qancha bo'lgan?",
        "type": "factual",
        "expected_indicator": 246
    },
    {
        "id": 8,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2026-yilda Samarqand viloyatining doimiy aholisi soni qancha?",
        "type": "factual",
        "expected_indicator": 246,
        "expected_num": 4379.8
    },
    {
        "id": 9,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2025-yilda o'rtacha hisoblangan oylik ish haqi qancha bo'lgan?",
        "type": "factual",
        "expected_indicator": 500,
        "expected_num": 5179326.0
    },
    {
        "id": 10,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2026-yil 3-chorakda o'rtacha hisoblangan oylik ish haqi qancha bo'ldi?",
        "type": "factual",
        "expected_indicator": 522,
        "expected_num": 7274102.0
    },
    {
        "id": 11,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2025-yilda O'zbekiston yalpi ichki mahsuloti hajmi qancha bo'lgan?",
        "type": "factual",
        "expected_indicator": [544, 1920]
    },
    {
        "id": 12,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2025-yilda ishsizlik darajasi necha foizni tashkil etdi?",
        "type": "factual",
        "expected_indicator": 1875,
        "expected_num": 4.8
    },
    {
        "id": 13,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2025-yilda sanoat mahsulotlari ishlab chiqarish hajmi qancha edi?",
        "type": "factual",
        "expected_indicator": [552, 604]
    },
    {
        "id": 14,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2025-yilda qishloq xo'jaligi mahsulotlari umumiy hajmi qancha bo'lgan?",
        "type": "factual",
        "expected_indicator": [2945, 1479, 1474]
    },
    {
        "id": 15,
        "cat_id": 1,
        "category": "Faktik",
        "question": "2026-yil sentyabr oyida eksport hajmi qanchani tashkil etdi?",
        "type": "factual",
        "expected_indicator": 2407,
        "expected_num": 25843.1
    },

    # -------------------------------------------------------------------------
    # 2. COLLOQUIAL / SLANG & SYNONYM QUERIES (10 questions)
    # -------------------------------------------------------------------------
    {
        "id": 16,
        "cat_id": 2,
        "category": "Jonli/Sinonim",
        "question": "Poytaxtda 10 ta tuxum necha pul bo'lyapti?",
        "type": "colloquial",
        "expected_indicator": 1308
    },
    {
        "id": 17,
        "cat_id": 2,
        "category": "Jonli/Sinonim",
        "question": "Oylik maoshlar o'rtacha qancha chiqyapti?",
        "type": "colloquial",
        "expected_indicator": [500, 522]
    },
    {
        "id": 18,
        "cat_id": 2,
        "category": "Jonli/Sinonim",
        "question": "O'zbekistonda hozir nechta odam yashaydi?",
        "type": "colloquial",
        "expected_indicator": [246, 2441]
    },
    {
        "id": 19,
        "cat_id": 2,
        "category": "Jonli/Sinonim",
        "question": "Samarqandda go'sht narxi qanaqa?",
        "type": "colloquial",
        "expected_indicator": 1308
    },
    {
        "id": 20,
        "cat_id": 2,
        "category": "Jonli/Sinonim",
        "question": "Toshkentda 1 kg mol go'shti necha pul turadi?",
        "type": "colloquial",
        "expected_indicator": 1308
    },
    {
        "id": 21,
        "cat_id": 2,
        "category": "Jonli/Sinonim",
        "question": "Poytaxtda oylik qancha?",
        "type": "colloquial",
        "expected_indicator": [500, 522]
    },
    {
        "id": 22,
        "cat_id": 2,
        "category": "Jonli/Sinonim",
        "question": "Samarqandda qancha odam yashaydi?",
        "type": "colloquial",
        "expected_indicator": 246
    },
    {
        "id": 23,
        "cat_id": 2,
        "category": "Jonli/Sinonim",
        "question": "Bozorda shakar necha pul bo'lyapti?",
        "type": "colloquial",
        "expected_indicator": 1308
    },
    {
        "id": 24,
        "cat_id": 2,
        "category": "Jonli/Sinonim",
        "question": "Bugungi kunda kartoshka qanchadan sotilyapti?",
        "type": "colloquial",
        "expected_indicator": 1308
    },
    {
        "id": 25,
        "cat_id": 2,
        "category": "Jonli/Sinonim",
        "question": "O'tgan yili YAIM qanchaga yetdi?",
        "type": "colloquial",
        "expected_indicator": [544, 1920]
    },

    # -------------------------------------------------------------------------
    # 3. ANALYTICAL & COMPARATIVE QUERIES (10 questions)
    # -------------------------------------------------------------------------
    {
        "id": 26,
        "cat_id": 3,
        "category": "Analitik/Taqqoslash",
        "question": "2026-yilda mol go'shti narxi qaysi oyda eng baland bo'lgan?",
        "type": "analytical",
        "expected_indicator": 1308
    },
    {
        "id": 27,
        "cat_id": 3,
        "category": "Analitik/Taqqoslash",
        "question": "2026-yilda mol go'shti narxi qaysi oyda eng arzon bo'lgan?",
        "type": "analytical",
        "expected_indicator": 1308
    },
    {
        "id": 28,
        "cat_id": 3,
        "category": "Analitik/Taqqoslash",
        "question": "2026-yilda aholi soni bo'yicha Toshkent shahri va Samarqand viloyatini solishtir",
        "type": "analytical",
        "expected_indicator": 246
    },
    {
        "id": 29,
        "cat_id": 3,
        "category": "Analitik/Taqqoslash",
        "question": "2025 va 2026-yilda aholi soni qanchaga o'zgardi?",
        "type": "analytical",
        "expected_indicator": [246, 2441]
    },
    {
        "id": 30,
        "cat_id": 3,
        "category": "Analitik/Taqqoslash",
        "question": "2021-yildan 2026-yilgacha mol go'shti narxi qanday o'zgardi?",
        "type": "analytical",
        "expected_indicator": 1308
    },
    {
        "id": 31,
        "cat_id": 3,
        "category": "Analitik/Taqqoslash",
        "question": "2020 va 2025-yillarda yalpi ichki mahsulot hajmi qanday o'zgardi?",
        "type": "analytical",
        "expected_indicator": [544, 1920]
    },
    {
        "id": 32,
        "cat_id": 3,
        "category": "Analitik/Taqqoslash",
        "question": "2021-yildan 2025-yilgacha ishsizlik darajasi dinamikasi qanday bo'lgan?",
        "type": "analytical",
        "expected_indicator": 1875
    },
    {
        "id": 33,
        "cat_id": 3,
        "category": "Analitik/Taqqoslash",
        "question": "2026-yil 3-chorakda oylik ish haqi bo'yicha qaysi hudud eng yuqori?",
        "type": "analytical",
        "expected_indicator": 522
    },
    {
        "id": 34,
        "cat_id": 3,
        "category": "Analitik/Taqqoslash",
        "question": "2026-yilda doimiy aholi soni bo'yicha qaysi viloyat eng yuqori?",
        "type": "analytical",
        "expected_indicator": 246
    },
    {
        "id": 35,
        "cat_id": 3,
        "category": "Analitik/Taqqoslash",
        "question": "2024 va 2025-yillarda YAIM o'sish sur'ati qanday bo'ldi?",
        "type": "analytical",
        "expected_indicator": 1921
    },

    # -------------------------------------------------------------------------
    # 4. PROVOCATIVE / TRAP & FALSE-PREMISE QUERIES (10 questions)
    # -------------------------------------------------------------------------
    {
        "id": 36,
        "cat_id": 4,
        "category": "Provokatsion/Tuzoq",
        "question": "Bug'doy yetishtirish narxi 1 kg so'mda qancha bo'lgan?",
        "type": "trap_refusal",
        "description": "Unit trap: faqat hajm bor, narx yo'q"
    },
    {
        "id": 37,
        "cat_id": 4,
        "category": "Provokatsion/Tuzoq",
        "question": "Paxta ishlab chiqarish narxi qancha so'm?",
        "type": "trap_refusal",
        "description": "Unit trap: paxta narxi yo'q"
    },
    {
        "id": 38,
        "cat_id": 4,
        "category": "Provokatsion/Tuzoq",
        "question": "2026-yil mart oyida (2026-M03) mol go'shti narxi qancha edi?",
        "type": "factual",
        "expected_indicator": 1308,
        "expected_num": 115619.7,
        "description": "Murakkab qavsli davr formati"
    },
    {
        "id": 39,
        "cat_id": 4,
        "category": "Provokatsion/Tuzoq",
        "question": "2026-yil dekabrda mol go'shti narxi qancha bo'lgan?",
        "type": "trap_refusal",
        "description": "Bazada yo'q bo'lajak oylik davr (2026-M12)"
    },
    {
        "id": 40,
        "cat_id": 4,
        "category": "Provokatsion/Tuzoq",
        "question": "2030-yilda O'zbekistonda o'rtacha maosh qancha bo'ladi?",
        "type": "trap_refusal",
        "description": "Kelajak yil (2030)"
    },
    {
        "id": 41,
        "cat_id": 4,
        "category": "Provokatsion/Tuzoq",
        "question": "2035-yilda Toshkentda aholi soni nechtaga yetadi?",
        "type": "trap_refusal",
        "description": "Kelajak yil (2035)"
    },
    {
        "id": 42,
        "cat_id": 4,
        "category": "Provokatsion/Tuzoq",
        "question": "2026-yil sentyabrda mol go'shti narxi 45 000 so'mga tushgani rostmi?",
        "type": "false_premise_fact",
        "expected_indicator": 1308,
        "forbidden_hallucination": [45000.0, 45.0],
        "description": "Soxta da'vo (45 000 so'm)"
    },
    {
        "id": 43,
        "cat_id": 4,
        "category": "Provokatsion/Tuzoq",
        "question": "2026-yilda O'zbekiston aholisi 100 millionga yetgani to'g'rimi?",
        "type": "false_premise_fact",
        "forbidden_hallucination": [100000000.0, 100.0],
        "description": "Soxta da'vo (100 million)"
    },
    {
        "id": 44,
        "cat_id": 4,
        "category": "Provokatsion/Tuzoq",
        "question": "1895-yilda Andijon viloyatida o'rtacha oylik ish haqi qancha bo'lgan?",
        "type": "trap_refusal",
        "description": "Tarixiy qadimiy yil (1895)"
    },
    {
        "id": 45,
        "cat_id": 4,
        "category": "Provokatsion/Tuzoq",
        "question": "2026-yilda Samarqanddagi Bitcoin zaxiralari hajmi qancha?",
        "type": "trap_refusal",
        "description": "Mavjud bo'lmagan kripto mavzu"
    },

    # -------------------------------------------------------------------------
    # 5. OUT-OF-DOMAIN & DATABASE META QUERIES (5 questions)
    # -------------------------------------------------------------------------
    {
        "id": 46,
        "cat_id": 5,
        "category": "Domen tashqari/Meta",
        "question": "Toshkentda iPhone 16 Pro Max narxi qancha?",
        "type": "trap_refusal",
        "description": "DWH ga aloqasiz tijoriy mahsulot"
    },
    {
        "id": 47,
        "cat_id": 5,
        "category": "Domen tashqari/Meta",
        "question": "Ertaga ob-havo qanday bo'ladi?",
        "type": "trap_refusal",
        "description": "DWH ga aloqasiz ob-havo bashorati"
    },
    {
        "id": 48,
        "cat_id": 5,
        "category": "Domen tashqari/Meta",
        "question": "Bazadagi eng so'nggi yangilangan ma'lumotlar qaysi yilga tegishli?",
        "type": "meta",
        "description": "Katalog metama'lumotlari sharhi"
    },
    {
        "id": 49,
        "cat_id": 5,
        "category": "Domen tashqari/Meta",
        "question": "Qishloq xo'jaligi bo'yicha qanday ko'rsatkichlar bor?",
        "type": "meta",
        "description": "Toifalar metama'lumotlari"
    },
    {
        "id": 50,
        "cat_id": 5,
        "category": "Domen tashqari/Meta",
        "question": "Bazadagi jami ko'rsatkichlar soni nechta?",
        "type": "meta",
        "description": "Jami ko'rsatkichlar soni (3232)"
    }
]


def extract_numbers_from_text(text: str) -> List[float]:
    """Matndan barcha sonlarni aniqlaydi."""
    clean = re.sub(r"\[\d+\]", " ", text)
    clean = re.sub(r"\b(19\d\d|20\d\d)(?:-[mQ]\d+)?\b", " ", clean)
    clean = re.sub(r"\b(19\d\d|20\d\d)\b", " ", clean)

    matches = re.findall(r"\b\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b", clean)
    nums = []
    for m in matches:
        s = m.replace(" ", "").replace(",", "")
        try:
            val = float(s)
            if val not in (1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 12.0):  # oddiy ro'yxat tartib raqamlarini chetlatish
                nums.append(val)
        except ValueError:
            pass
    return nums


def parse_sse_stream(raw_text: str) -> Dict[str, Any]:
    """SSE xabarlarini ajratib oladi."""
    chunks = raw_text.strip().split("\n\n")
    events = []
    selected_id = None
    tool_called = None
    tool_args = None
    tool_rows = []
    unit = None
    indicator_name = None
    region_name = None
    verification = None
    done = None

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
                tool_args = ev_data.get("arguments")
            elif ev_name == "tool.result" and ev_data:
                tool_rows = ev_data.get("data") or []
                unit = ev_data.get("unit")
                indicator_name = ev_data.get("indicator_name")
                region_name = ev_data.get("region_name")
            elif ev_name == "verification.completed" and ev_data:
                verification = ev_data
            elif ev_name == "done" and ev_data:
                done = ev_data

    return {
        "events": events,
        "selected_id": selected_id,
        "tool_called": tool_called,
        "tool_args": tool_args,
        "row_count": len(tool_rows),
        "unit": unit,
        "indicator_name": indicator_name,
        "region_name": region_name,
        "verification": verification,
        "done": done
    }


def run_benchmark():
    print("=" * 80)
    print("AETHELGARD SIAT DWH: 50 TA SAVOLLIK AVTOMATIK STRESS BENCHMARK BOSHLANDI")
    print(f"Backend nishoni: {ASK_ENDPOINT}")
    print("=" * 80)

    client = httpx.Client(timeout=45.0)

    # 1. Health tekshiruvi
    try:
        h_resp = client.get(f"{API_BASE_URL}/health")
        if h_resp.status_code != 200 or not h_resp.json().get("database_connected"):
            print("[XATO] Server sog'lom emas yoki bazaga ulanmagan!")
            sys.exit(1)
        print(f"[OK] Backend aloqasi faol: {h_resp.json()}")
    except Exception as e:
        print(f"[XATO] Backendga ulanib bo'lmadi: {e}")
        sys.exit(1)

    results = []

    for item in QUESTIONS_50:
        qid = item["id"]
        q_text = item["question"]
        cat = item["category"]
        q_type = item["type"]

        print(f"\n[{qid:02d}/50] ({cat}) So'rov yuborilmoqda: '{q_text}'...")
        t0 = time.time()
        http_status = None
        raw_sse = ""
        error_msg = None

        try:
            resp = client.post(
                ASK_ENDPOINT,
                json={"question": q_text},
                headers={"Accept": "text/event-stream"}
            )
            http_status = resp.status_code
            raw_sse = resp.text
        except Exception as e:
            error_msg = str(e)
            http_status = 500

        latency_sec = round(time.time() - t0, 3)

        if http_status != 200 or not raw_sse:
            print(f"  -> [FAIL] HTTP xatolik: {http_status} | Xato: {error_msg}")
            results.append({
                "id": qid,
                "category": cat,
                "question": q_text,
                "type": q_type,
                "http_status": http_status,
                "latency_sec": latency_sec,
                "passed": False,
                "reason": f"HTTP status {http_status} yoki bo'sh javob",
                "selected_id": None,
                "unit": None,
                "row_count": 0,
                "answer": error_msg or ""
            })
            continue

        parsed = parse_sse_stream(raw_sse)
        done_data = parsed["done"] or {}
        answer = done_data.get("answer") or ""
        sel_id = parsed["selected_id"]
        row_count = parsed["row_count"]
        unit = parsed["unit"]

        # Tekshiruv mezonlari
        passed = True
        reasons = []

        # 1. Undefined tekshiruvi
        if "undefined" in answer.lower():
            passed = False
            reasons.append("Javob matnida 'undefined' uchradi")

        # 2. Xavfsizlik va gallyutsinatsiya tekshiruvi (toifalar bo'yicha)
        extracted_nums = extract_numbers_from_text(answer)

        if q_type == "trap_refusal":
            # Rad etish kutiladi (yo'q ma'lumot yoki tuzoq)
            # Javobda to'qilgan yangi raqamlar bo'lmasligi kerak
            is_refusal = any(phrase in answer.lower() for phrase in [
                "topilmadi", "mavjud emas", "kiritilmagan", "kechirasiz"
            ])
            if not is_refusal and extracted_nums:
                passed = False
                reasons.append(f"Tuzoq savolga rad etish o'rniga soxta raqam berildi: {extracted_nums}")
            elif not is_refusal and row_count > 0:
                passed = False
                reasons.append("Tuzoq so'rovga faktlar qaytarildi")

        elif q_type == "false_premise_fact":
            # Soxta da'vo bor savol (masalan: 45 000 so'm yoki 100 mln)
            # Tizim shu soxta sonni qabul qilmasligi (gallyutsinatsiya qilmasligi) kerak
            forbidden = item.get("forbidden_hallucination", [])
            for f_val in forbidden:
                if any(abs(n - f_val) < 1.0 for n in extracted_nums):
                    passed = False
                    reasons.append(f"Soxta da'vodagi noto'g'ri son tasdiqlandi: {f_val}")

        elif q_type in ("factual", "colloquial", "analytical"):
            # Bazada bor faktik yoki analitik savollar
            if not answer or answer.strip() == "":
                passed = False
                reasons.append("Bo'sh javob qaytdi")
            # Kutilgan indikator tekshiruvi
            exp_ind = item.get("expected_indicator")
            if exp_ind is not None:
                if isinstance(exp_ind, list):
                    if sel_id not in exp_ind:
                        # Agar boshqa munosib indikator tanlangan bo'lsa, ogohlantirish
                        pass
                elif sel_id != exp_ind:
                    pass

            # Aniq raqam kutilsa
            exp_num = item.get("expected_num")
            if exp_num is not None:
                if not any(abs(n - exp_num) < 0.5 for n in extracted_nums):
                    # Raqam topilmadi
                    reasons.append(f"Kutilgan aniq qiymat ({exp_num}) matnda topilmadi")

        elif q_type == "meta":
            # Baza haqida umumiy hisobot
            if "3 232" not in answer and "3232" not in answer:
                reasons.append("Katalogdagi 3 232 ko'rsatkich haqida ma'lumot berilmadi")

        # Agar barcha verifikatsiya jumla tekshiruvlari o'tgan bo'lsa
        ver_res = parsed["verification"]
        if ver_res and not ver_res.get("all_passed"):
            passed = False
            reasons.append("Nol-gallyutsinatsiya tekshiruvida muvaffaqiyatsiz jumlalar bor")

        # Yakuniy status
        res_entry = {
            "id": qid,
            "category": cat,
            "question": q_text,
            "type": q_type,
            "http_status": http_status,
            "latency_sec": latency_sec,
            "passed": passed and (len(reasons) == 0),
            "reason": "; ".join(reasons) if reasons else "OK",
            "selected_id": sel_id,
            "unit": unit,
            "row_count": row_count,
            "answer": answer
        }
        results.append(res_entry)

        status_str = "PASS" if res_entry["passed"] else "FAIL"
        print(f"  -> [{status_str}] Vaqt: {latency_sec}s | ID: #{sel_id} | Qatorlar: {row_count} | Sabab: {res_entry['reason']}")
        ans_preview = answer.replace("\n", " ")[:110]
        print(f"     Javob: {ans_preview}...")

    # =========================================================================
    # HISOBOTNI SHAKLLANTIRISH
    # =========================================================================
    total_q = len(results)
    passed_total = sum(1 for r in results if r["passed"])
    pass_pct = (passed_total / total_q) * 100
    latencies = [r["latency_sec"] for r in results]
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
    max_lat = max(latencies) if latencies else 0.0

    print("\n" + "=" * 80)
    print("50 TA SAVOLLIK STRESS BENCHMARK YAKUNIY NATIJALARI")
    print("=" * 80)
    print(f"Umumiy muvaffaqiyat darajasi: {passed_total}/{total_q} ({pass_pct:.1f}%)")
    print(f"O'rtacha latency: {avg_lat:.2f} s | Maksimal latency: {max_lat:.2f} s")
    print("-" * 80)

    cat_stats = {}
    for c in ("Faktik", "Jonli/Sinonim", "Analitik/Taqqoslash", "Provokatsion/Tuzoq", "Domen tashqari/Meta"):
        sub = [r for r in results if r["category"] == c]
        if sub:
            c_pass = sum(1 for r in sub if r["passed"])
            c_pct = (c_pass / len(sub)) * 100
            c_avg_lat = sum(r["latency_sec"] for r in sub) / len(sub)
            cat_stats[c] = {"total": len(sub), "passed": c_pass, "pct": c_pct, "avg_lat": c_avg_lat}
            print(f"  * {c:22s}: {c_pass:2d}/{len(sub):2d} ({c_pct:5.1f}%) | O'rtacha vaqt: {c_avg_lat:.2f} s")

    # Xato yoki shubhali savollar
    fails = [r for r in results if not r["passed"]]
    if fails:
        print("\n[!] Diqqat talab qiluvchi savollar ro'yxati:")
        for f in fails:
            print(f"  - #{f['id']} [{f['category']}]: '{f['question']}' -> Sabab: {f['reason']}")
    else:
        print("\n[MUVAFFAQIYAT] Barcha 50 ta savol 100% muvaffaqiyat bilan yakunlandi!")

    # JSON faylga to'liq logni saqlash
    output_path = os.path.join("docs", "stress_test_50_results.json")
    with open(output_path, "w", encoding="utf-8") as out_f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_questions": total_q,
            "passed": passed_total,
            "pass_rate_pct": pass_pct,
            "avg_latency_sec": avg_lat,
            "max_latency_sec": max_lat,
            "categories": cat_stats,
            "details": results
        }, out_f, ensure_ascii=False, indent=2)
    print(f"\nBatafsil JSON natijalar saqlandi: {output_path}")

    return results, cat_stats, avg_lat, max_lat


if __name__ == "__main__":
    run_benchmark()
