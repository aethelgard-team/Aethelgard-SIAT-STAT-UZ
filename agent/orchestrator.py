"""
=============================================================================
SIAT STAT DWH: Agent and SSE Orchestrator (agent/orchestrator.py)
Loyiha: siat.stat.uz MCP Loyihasi
Muallif: Siddiq (Backend & Database Lead)
Tavsif:
  Google Gemini LLM, MCP Tools va Zero-Hallucination Verifier modullarini
  birlashtirib, frontend uchun 7 bosqichli Server-Sent Events (SSE) oqimini
  generatsiya qiluvchi asosiy orkestrator.
=============================================================================
"""

import os
import re
import json
import time
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

from mcp_server import tools
from agent.verifier import verify_text

# .env yuklash
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL") or "gemini-3.8-flash"

# Gemini Client initsializatsiyasi
_gemini_client = None


def get_gemini_client():
    global _gemini_client
    if _gemini_client is None and GEMINI_API_KEY:
        try:
            from google import genai
            _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            print(f"[!] Gemini Client yaratishda ogohlantirish: {e}")
            _gemini_client = None
    return _gemini_client


def detect_language(text: str) -> str:
    """Savol tilini aniqlaydi (uz, ru, en)."""
    t = text.lower()
    # Ruscha harflar (кириллица)
    if re.search(r"[\u0400-\u04FF]", t):
        if any(w in t for w in ["narxi", "qancha", "necha", "yili", "oyida", "ko'rsatkich"]):
            return "uz"  # O'zbek kirillcha
        return "ru"
    # Inglizcha kalit so'zlar
    if any(w in t for w in ["what", "how", "price", "rate", "average", "in", "the", "when"]):
        return "en"
    return "uz"


def parse_and_clean_question(query: str) -> Tuple[str, str, Optional[str], Optional[str]]:
    """
    Savolni tahlil qilib:
    - Tilni (uz, ru, en)
    - Tozalangan qidiruv kalit so'zlarini
    - Davrni (masalan: 2026-M09)
    - Mahsulot kodini (masalan: 017)
    ajratib oladi.
    """
    q_norm = re.sub(r"['`’‘ʻ]", "'", query.lower().strip())
    lang = detect_language(q_norm)

    # 1. Yil
    year_match = re.search(r"\b(19\d\d|20\d\d)\b", q_norm)
    year = int(year_match.group(1)) if year_match else None

    # 2. Oy nomlari
    month_map = {
        "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4,
        "may": 5, "iyun": 6, "iyul": 7, "avgust": 8,
        "sentyabr": 9, "sentabr": 9, "oktyabr": 10, "oktabr": 10,
        "noyabr": 11, "dekabr": 12,
        "январ": 1, "феврал": 2, "март": 3, "апрел": 4,
        "май": 5, "июн": 6, "июл": 7, "август": 8,
        "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12,
        "january": 1, "february": 2, "march": 3, "april": 4,
        "june": 6, "july": 7, "august": 8, "september": 9,
        "october": 10, "november": 11, "december": 12
    }

    month = None
    for m_name, m_num in month_map.items():
        if m_name in q_norm:
            month = m_num
            break

    target_period = None
    if year and month:
        target_period = f"{year}-M{month:02d}"
    elif year:
        target_period = str(year)

    # 3. Mahsulot / klassifikator
    target_item_code = None
    if "mol go'sht" in q_norm or "mol gosht" in q_norm or "говядин" in q_norm or "beef" in q_norm:
        target_item_code = "017"

    # 4. Qidiruv kalit so'zlarini tozalash (sana va so'roq so'zlarini chiqarib tashlash)
    cleaned = q_norm
    cleaned = re.sub(r"\b(19|20)\d\d(?:-yil(?:da)?)?\b", "", cleaned)
    for m_name in month_map.keys():
        cleaned = re.sub(rf"\b{m_name}(?:da|i|oyida)?\b", "", cleaned)

    # Grammatik va statistik shovqin so'zlar
    stopwords = {
        "qancha", "necha", "nechta", "edi", "bo'lgan", "bolgan", "nima", "qayerda",
        "oyida", "yili", "uchun", "o'rtacha", "ortacha", "dinamikasi", "miqdori",
        "darajasi", "haqida", "qanday", "berilgan", "tashkil"
    }

    words = []
    for w in re.findall(r"[a-zA-Z0-9\u0400-\u04FF']+", cleaned):
        w_stem = re.sub(r"(ning|ni|dagi|dan|ga|da)$", "", w)
        if len(w_stem) >= 3 and w_stem not in stopwords and w not in stopwords:
            words.append(w_stem)

    core_search = " ".join(words)
    if ("narx" in q_norm or "baho" in q_norm or "price" in q_norm) and "narx" not in core_search:
        core_search += " narxi"
    if not core_search:
        core_search = q_norm

    return lang, core_search.strip(), target_period, target_item_code


def format_sse(event: str, data: Dict[str, Any]) -> str:
    """Server-Sent Event formatida satr shakllantiradi."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def orchestrate_question(question: str) -> AsyncGenerator[str, None]:
    """
    Foydalanuvchi savolini qabul qilib, 7 bosqichli SSE oqimini generatsiya qiluvchi
    asosiy asinxron orkestrator generatori.
    """
    start_total_time = time.time()

    try:
        # =====================================================================
        # 1-BOSQICH: Savolni tahlil qilish (parse)
        # =====================================================================
        yield format_sse("stage.started", {
            "stage": "parse",
            "message": "Savol tahlil qilinmoqda va normallashtirilmoqda..."
        })
        await asyncio.sleep(0.01)

        lang, search_keywords, target_period, target_item_code = parse_and_clean_question(question)

        yield format_sse("stage.completed", {
            "stage": "parse",
            "lang": lang,
            "normalized_query": search_keywords,
            "detected_period": target_period,
            "detected_item_code": target_item_code
        })
        await asyncio.sleep(0.01)

        # =====================================================================
        # 2-BOSQICH: Katalogdan qidirish (search)
        # =====================================================================
        yield format_sse("stage.started", {
            "stage": "search",
            "message": "DWH katalogidan RRF gibrid qidiruv amalga oshirilmoqda..."
        })

        search_t0 = time.time()
        search_res = tools.search_indicators(search_keywords, limit=5)
        search_dur_ms = round((time.time() - search_t0) * 1000, 2)

        if not search_res["results"]:
            # Agar topilmasa butun so'rov bilan qayta qidirish
            search_res = tools.search_indicators(question, limit=5)

        selected_indicator_id = None
        if search_res["results"]:
            selected_indicator_id = search_res["results"][0]["indicator_id"]

        yield format_sse("search.completed", {
            "stage": "search",
            "query": search_keywords,
            "execution_ms": search_dur_ms,
            "selected_indicator_id": selected_indicator_id,
            "total_matches": search_res["count"],
            "results": search_res["results"]
        })

        yield format_sse("stage.completed", {
            "stage": "search",
            "selected_indicator_id": selected_indicator_id
        })
        await asyncio.sleep(0.01)

        if not selected_indicator_id:
            yield format_sse("done", {
                "answer": "Kechirasiz, ushbu so'rov bo'yicha bazada mos statistik ko'rsatkich topilmadi.",
                "sources": [],
                "all_passed": True
            })
            return

        # =====================================================================
        # 3-BOSQICH: MCP Tool chaqiruvi (tool)
        # =====================================================================
        tool_name = "get_data"
        tool_args = {
            "indicator_id": selected_indicator_id,
            "item_codes": [target_item_code] if target_item_code else None,
            "periods": [target_period] if target_period else None,
            "limit": 100
        }

        yield format_sse("tool.called", {
            "stage": "tool",
            "call_id": "call_mcp_1",
            "tool": tool_name,
            "arguments": tool_args
        })
        await asyncio.sleep(0.01)

        # =====================================================================
        # 4-BOSQICH: DWH omboridan o'qish (dwh)
        # =====================================================================
        yield format_sse("stage.started", {
            "stage": "dwh",
            "table": "dwh.fact_value",
            "message": f"DWH bazasidan #{selected_indicator_id} ko'rsatkich ma'lumotlari o'qilmoqda..."
        })

        dwh_t0 = time.time()
        dwh_data = tools.get_data(
            indicator_id=selected_indicator_id,
            item_codes=tool_args["item_codes"],
            periods=tool_args["periods"],
            limit=tool_args["limit"]
        )
        meta_data = tools.get_indicator_metadata(selected_indicator_id)
        dwh_dur_ms = round((time.time() - dwh_t0) * 1000, 2)

        yield format_sse("stage.completed", {
            "stage": "dwh",
            "table": "dwh.fact_value",
            "execution_ms": dwh_dur_ms,
            "rows_count": dwh_data["total_returned"]
        })
        await asyncio.sleep(0.01)

        # =====================================================================
        # 5-BOSQICH: Natijani taqdim etish (result)
        # =====================================================================
        yield format_sse("tool.result", {
            "stage": "result",
            "call_id": "call_mcp_1",
            "tool": tool_name,
            "execution_ms": dwh_dur_ms,
            "table": "dwh.fact_value",
            "indicator_name": meta_data.get("name_uz"),
            "unit": meta_data.get("unit_uz"),
            "data": dwh_data["data"]
        })
        await asyncio.sleep(0.01)

        # =====================================================================
        # 6-BOSQICH: Javobni generatsiya qilish (generate)
        # =====================================================================
        yield format_sse("stage.started", {
            "stage": "generate",
            "message": "Nol-gallyutsinatsiya qoidasi asosida javob shakllantirilmoqda..."
        })

        # Javob matnini tayyorlash
        raw_llm_text = ""
        facts = dwh_data["data"]

        # 1-variant: Gemini API orqali generatsiya qilib ko'rish
        gemini_client = get_gemini_client()
        gemini_succeeded = False

        if gemini_client and facts:
            try:
                system_instruction = (
                    "Siz O'zbekiston Davlat statistika qo'mitasi rasmiy ma'lumotlar bazasi analitikasisiz. "
                    "Qat'iy qoidalar:\n"
                    "1. Raqam faqat berilgan DWH natijalaridan olinishi shart!\n"
                    "2. Birorta ham taxminiy yoki to'qilgan raqam kiritilmasin!\n"
                    "3. Har bir tasdiqlangan raqamdan keyin [1] manba havolasi qo'yilsin.\n"
                    "4. Javob o'zbek tilida, lo'nda va professional bo'lsin."
                )
                prompt = (
                    f"Foydalanuvchi savoli: '{question}'\n\n"
                    f"DWH Bazadan olingan ma'lumotlar:\n"
                    f"Ko'rsatkich: {meta_data.get('name_uz')}\n"
                    f"O'lchov birligi: {meta_data.get('unit_uz')}\n"
                    f"Faktlar: {json.dumps(facts[:10], ensure_ascii=False)}\n\n"
                    f"Yuqoridagi ma'lumotlar asosida savolga aniq va qisqa javob yozing."
                )

                # Timeout 5 soniya bilan chaqirish
                resp = await asyncio.wait_for(
                    asyncio.to_thread(
                        gemini_client.models.generate_content,
                        model=LLM_MODEL,
                        contents=prompt,
                        config={"temperature": 0.0}
                    ),
                    timeout=5.0
                )
                if resp and resp.text:
                    raw_llm_text = resp.text.strip()
                    gemini_succeeded = True
            except Exception:
                gemini_succeeded = False

        # 2-variant: Agar Gemini javob bermasa yoki tarmoq sekin bo'lsa,
        # DWH faktlaridan bevosita aniq va mukammal deterministik javob quriladi
        if not gemini_succeeded or not raw_llm_text:
            if facts:
                fact0 = facts[0]
                item_name = fact0.get("item_name", "ko'rsatkich")
                period_str = fact0.get("period_key", "")
                val = fact0.get("value")
                unit_str = meta_data.get("unit_uz", "so'mda")

                if val is not None:
                    raw_llm_text = (
                        f"{period_str} holatiga ko'ra, {item_name}ning o'rtacha qiymati "
                        f"{val:,.1f} {unit_str}ni tashkil etgan [1]."
                    )
                else:
                    raw_llm_text = (
                        f"{period_str} davri uchun {item_name} bo'yicha ma'lumot kiritilmagan "
                        f"(mavsumiy xususiyatga ega) [1]."
                    )
            else:
                raw_llm_text = "Ushbu so'rov bo'yicha bazada aniq statistik qiymat topilmadi [1]."

        # Oqimli (streaming) delta voqealari
        words = raw_llm_text.split(" ")
        for i, word in enumerate(words):
            delta = word + (" " if i < len(words) - 1 else "")
            yield format_sse("generation.delta", {
                "stage": "generate",
                "delta": delta
            })
            await asyncio.sleep(0.01)

        yield format_sse("stage.completed", {
            "stage": "generate",
            "raw_text": raw_llm_text
        })
        await asyncio.sleep(0.01)

        # =====================================================================
        # 7-BOSQICH: Nol-gallyutsinatsiya verifikatsiyasi (verify)
        # =====================================================================
        yield format_sse("stage.started", {
            "stage": "verify",
            "message": "Generatsiya qilingan raqamlar DWH faktlari bilan verifikatsiya qilinmoqda..."
        })

        verification_result = verify_text(raw_llm_text, dwh_data)

        yield format_sse("verification.completed", {
            "stage": "verify",
            "all_passed": verification_result["all_passed"],
            "total_sentences": verification_result["total_sentences"],
            "passed_count": verification_result["passed_sentences_count"],
            "failed_count": verification_result["failed_sentences_count"],
            "checklist": verification_result["sentences"]
        })

        yield format_sse("stage.completed", {
            "stage": "verify"
        })
        await asyncio.sleep(0.01)

        # =====================================================================
        # YAKUNIY BOSQICH: done (Tasdiqlangan javob va manbalar)
        # =====================================================================
        snapshot_date = facts[0].get("snapshot_date") if facts else "2026-11-11"
        source_url = meta_data.get("source_url") or f"https://api.siat.stat.uz/media/uploads/sdmx/sdmx_data_{selected_indicator_id}.json"

        sources = [{
            "n": 1,
            "indicator_id": selected_indicator_id,
            "name": meta_data.get("name_uz"),
            "url": source_url,
            "snapshot_date": str(snapshot_date)
        }]

        yield format_sse("done", {
            "answer": verification_result["verified_text"],
            "sources": sources,
            "all_passed": verification_result["all_passed"],
            "total_duration_ms": round((time.time() - start_total_time) * 1000, 2)
        })

    except Exception as e:
        yield format_sse("error", {
            "message": f"Orkestratsiya jarayonida xatolik yuz berdi: {str(e)}"
        })
