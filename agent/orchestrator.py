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
from mcp_server.db import get_db_cursor
from agent.verifier import verify_text

# .env yuklash
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL") or "gemini-3.8-flash"

# Gemini Client initsializatsiyasi va circuit breaker
_gemini_client = None
_gemini_consecutive_failures = 0

MONTH_MAP = {
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

REGION_PATTERNS = [
    ("toshkent shahri", "toshkent shahri"),
    ("toshkent viloyati", "toshkent viloyati"),
    ("qoraqalpog'iston", "qoraqalpog'iston"),
    ("qoraqalpogiston", "qoraqalpog'iston"),
    ("samarqand", "samarqand"),
    ("andijon", "andijon"),
    ("buxoro", "buxoro"),
    ("farg'ona", "farg'ona"),
    ("fargona", "farg'ona"),
    ("namangan", "namangan"),
    ("xorazm", "xorazm"),
    ("qashqadaryo", "qashqadaryo"),
    ("surxondaryo", "surxondaryo"),
    ("navoiy", "navoiy"),
    ("jizzax", "jizzax"),
    ("sirdaryo", "sirdaryo"),
    ("toshkent", "toshkent"),
]

# Qidiruv va mavzu tekshiruvi uchun umumiy yordamchi/shovqin so'zlar
STOPWORDS = {
    "qancha", "necha", "nechta", "nechi", "edi", "bo'lgan", "bolgan", "bo'ldi",
    "boldi", "bo'ladi", "boladi", "etdi", "tashkil", "nima", "qayerda", "qanday",
    "qaysi", "haqida", "berilgan", "ko'ra", "kora", "holatiga", "yil", "yilda",
    "yili", "yillarda", "yillar", "yilgacha", "yildan", "chorak", "chorakda",
    "choraklik", "oy", "oyda", "oyida", "va", "hamda", "bilan", "uchun", "foiz",
    "foizni", "foizda", "eng", "yuqori", "past", "katta", "kichik", "o'rtacha",
    "ortacha", "dinamika", "dinamikasi", "miqdor", "miqdori", "daraja", "darajasi",
    "ko'rsatkich", "korsatkich", "ko'rsatkichi", "statistika", "statistikasi",
    "o'sdi", "osdi", "o'zgardi", "ozgardi", "o'zgarish", "ozgarish", "davomida",
    "orasida", "nisbatan", "solishtirganda", "taqqoslang", "solishtiring", "reyting",
    "qayd", "etilgan", "qilib", "barcha", "jami", "respublika", "respublikasi",
    "viloyat", "viloyati", "viloyatda", "hudud", "hududda", "hududlar", "kesimida",
    "mamlakat", "mamlakatda", "bo'yicha", "boyicha"
}

# Asosiy predmetni tekshirishda ixtiyoriy bo'lgan statistik sifatlar
GENERIC_ATTRIBUTE_STEMS = {
    "narx", "qiymat", "hajm", "son", "miqdor", "daraja", "ulush", "foiz",
    "indeks", "sur'at", "o'sish", "osish", "tovar", "mahsulot", "xizmat",
    "respublika", "viloyat", "shahar", "tuman", "o'rtacha", "ortacha", "oylik",
    "yillik", "choraklik", "davlat", "umumiy", "jami", "nomi", "boshiga"
}

SYNONYM_MAP = {
    "yaim": "yalpi ichki mahsulot",
    "yhm": "yalpi hududiy mahsulot",
    "inflyatsiya": "iste'mol narxlari indeksi",
    "maosh": "ish haqi",
}


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
    if re.search(r"[\u0400-\u04FF]", t):
        if any(w in t for w in ["narxi", "qancha", "necha", "yili", "oyida", "ko'rsatkich"]):
            return "uz"
        return "ru"
    if any(w in t for w in ["what", "how", "price", "rate", "average", "when"]):
        return "en"
    return "uz"


def _stem_uz_token(word: str) -> str:
    """O'zbekcha so'z qo'shimchalarini yengil qisqartiradi."""
    w = re.sub(r"['`’‘ʻ]", "'", word.lower().strip())
    if len(w) <= 4:
        return w
    for suf in ("lardagi", "larining", "lari", "ining", "ning", "dagi", "gacha", "lar", "ini", "dan", "ni", "ga", "da", "si"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    if w.endswith("i") and len(w) >= 5 and w not in ("yalpi", "ichki", "oylik", "yillik", "ishsizlik", "aholi", "navoiy"):
        return w[:-1]
    return w


def analyze_question_full(query: str) -> Dict[str, Any]:
    """
    Savolni to'liq tahlil qilib, davrlar, hudud, mahsulot, niyat (intent) va
    qidiruv/mavzu tokenlarini ajratib oladi.
    """
    q_norm = re.sub(r"['`’‘ʻ]", "'", query.lower().strip())
    lang = detect_language(q_norm)

    # 1. Barcha yillar (1800..2099, shu jumladan 1920, 2032 va h.k. tuzoqlar uchun)
    years = [int(y) for y in re.findall(r"\b(1[89]\d\d|20\d\d)\b", q_norm)]

    # 2. Chorak (1-chorak, 3-chorak, Q3)
    quarter = None
    q_match = re.search(r"\b([1-4])[-\s]*chorak|\bq([1-4])\b", q_norm)
    if q_match:
        quarter = int(q_match.group(1) or q_match.group(2))

    # 3. Oy nomlari
    month = None
    for m_name, m_num in MONTH_MAP.items():
        if re.search(rf"\b{re.escape(m_name)}", q_norm):
            month = m_num
            break

    # 4. Maqsadli davrlar ro'yxati
    periods: List[str] = []
    if len(years) == 1 and month:
        periods = [f"{years[0]}-M{month:02d}"]
    elif len(years) == 1 and quarter:
        periods = [f"{years[0]}-Q{quarter}"]
    elif years:
        periods = [str(y) for y in years]

    # 5. Hududni ajratish
    region_hint = None
    for pat, canonical in REGION_PATTERNS:
        if pat in q_norm:
            region_hint = canonical
            break
    if not region_hint and ("o'zbekiston" in q_norm or "ozbekiston" in q_norm):
        region_hint = "o'zbekiston"

    # 6. Ma'lum mahsulotlar
    target_item_code = None
    if "mol go'sht" in q_norm or "mol gosht" in q_norm or "говядин" in q_norm or "beef" in q_norm:
        target_item_code = "017"

    # 7. Intent (so'rov turi) aniqlash
    is_region_cmp = any(w in q_norm for w in (
        "qaysi viloyat", "qaysi hudud", "hududlar", "viloyatlar",
        "eng yuqori", "eng past", "reyting", "taqqosla", "solishtir"
    )) and len(years) <= 1
    is_dynamics = (
        len(years) >= 2
        or any(w in q_norm for w in ("dinamik", "o'zgardi", "ozgardi", "o'sish", "osish", "kamay", "yildan", "yilgacha", "davomida"))
    )

    if is_region_cmp:
        intent = "compare_regions"
    elif is_dynamics:
        intent = "time_series"
    else:
        intent = "get_data"

    # 8. Qidiruv va mavzu kalit so'zlarini tozalash
    cleaned = q_norm
    cleaned = re.sub(r"\b(1[89]\d\d|20\d\d)(?:[-\s]*(?:yil(?:da|i|gacha|dan|larda)?))?\b", " ", cleaned)
    cleaned = re.sub(r"\b[1-4][-\s]*chorak(?:da|lik|i)?\b", " ", cleaned)
    for m_name in MONTH_MAP.keys():
        cleaned = re.sub(rf"\b{re.escape(m_name)}(?:da|i|oyida)?\b", " ", cleaned)

    # Mamlakat nomini qidiruv shovqinidan chiqarish (hudud sifatida alohida saqlanadi)
    cleaned_no_country = re.sub(r"\bo['`]?zbekiston(?:ning|da|dagi|ga|dan|i)?\b", " ", cleaned)
    cleaned_no_country = re.sub(r"\bress?publikasi(?:da|ning|ga)?\b", " ", cleaned_no_country)

    # Agar hudud nomi matnda bo'lsa (masalan "Toshkentda", "Samarqanddagi"), uni qidiruvda qoldirish ixtiyoriy,
    # lekin item resolution uchun region_hint ishlatamiz; umumiy qidiruvda hududni tozalab ko'rsatkich nomini topamiz
    search_source = cleaned_no_country
    if region_hint and region_hint != "o'zbekiston":
        search_source = re.sub(rf"\b{re.escape(region_hint)}(?:ning|dagi|dan|ga|da|i)?\b", " ", search_source)

    raw_words = re.findall(r"[a-zA-Z0-9\u0400-\u04FF']+", search_source)
    search_words: List[str] = []
    topic_tokens: List[str] = []

    for w in raw_words:
        w_clean = w.strip("'")
        if len(w_clean) < 3:
            continue
        w_stem = _stem_uz_token(w_clean)
        if w_clean in STOPWORDS or w_stem in STOPWORDS:
            continue

        # Sinonimlarni kengaytirish
        if w_clean in SYNONYM_MAP:
            syn_words = SYNONYM_MAP[w_clean].split()
            search_words.extend(syn_words)
            topic_tokens.extend(_stem_uz_token(sw) for sw in syn_words)
            continue

        search_words.append(w_clean)
        topic_tokens.append(w_stem)

    core_search = " ".join(search_words).strip()
    if ("narx" in q_norm or "baho" in q_norm or "price" in q_norm) and "narx" not in core_search:
        core_search = (core_search + " narxi").strip()
    if not core_search:
        core_search = q_norm

    return {
        "lang": lang,
        "core_search": core_search,
        "target_period": periods[0] if periods else None,
        "periods": periods,
        "years": years,
        "quarter": quarter,
        "month": month,
        "region_hint": region_hint,
        "target_item_code": target_item_code,
        "intent": intent,
        "topic_tokens": topic_tokens,
    }


def parse_and_clean_question(query: str) -> Tuple[str, str, Optional[str], Optional[str]]:
    """Orqaga moslik (backwards-compatible) uchun tahlil wrapper funksiyasi."""
    info = analyze_question_full(query)
    return info["lang"], info["core_search"], info["target_period"], info["target_item_code"]


def _normalize_for_match(text: str) -> str:
    return re.sub(r"['`’‘ʻ]", "'", (text or "").lower())


def _select_best_candidate_and_item(
    candidates: List[Dict[str, Any]],
    parsed: Dict[str, Any]
) -> Tuple[Optional[int], Optional[str], bool]:
    """
    Nomzod ko'rsatkichlar orasidan mavzuga 100% mos keladiganini tanlaydi va
    dim_item ichidan mos item_code ni aniqlaydi.

    Returns:
        (selected_indicator_id, resolved_item_code, topic_is_valid)
    """
    if not candidates:
        return None, None, False

    cand_ids = [c["indicator_id"] for c in candidates[:6]]
    items_by_ind: Dict[int, List[Dict[str, str]]] = {iid: [] for iid in cand_ids}
    year_bounds: Dict[int, Tuple[Optional[int], Optional[int]]] = {}

    with get_db_cursor() as cur:
        cur.execute("""
            SELECT indicator_id, item_code, name_uz
            FROM dwh.dim_item
            WHERE indicator_id = ANY(%s)
            ORDER BY item_code ASC;
        """, (cand_ids,))
        for r in cur.fetchall():
            items_by_ind[r["indicator_id"]].append({
                "item_code": r["item_code"],
                "name_uz": r["name_uz"] or ""
            })

        # Indeks yordamida har bir nomzodning min/max yilini tezkor olish
        for iid in cand_ids:
            cur.execute("""
                SELECT min(period_key) AS min_p, max(period_key) AS max_p
                FROM dwh.fact_value
                WHERE indicator_id = %s;
            """, (iid,))
            row = cur.fetchone()
            min_y = int(row["min_p"][:4]) if row and row["min_p"] and row["min_p"][:4].isdigit() else None
            max_y = int(row["max_p"][:4]) if row and row["max_p"] and row["max_p"][:4].isdigit() else None
            year_bounds[iid] = (min_y, max_y)

    # Asosiy predmet tokenlari (umumiy atributlardan tashqari)
    core_tokens = [
        t for t in parsed["topic_tokens"]
        if t not in GENERIC_ATTRIBUTE_STEMS and len(t) >= 3
    ]
    if not core_tokens:
        core_tokens = [t for t in parsed["topic_tokens"] if len(t) >= 3]

    wanted_periodicity = None
    if parsed["month"]:
        wanted_periodicity = "oylik"
    elif parsed["quarter"]:
        wanted_periodicity = "choraklik"
    elif parsed["years"] and not parsed["month"] and not parsed["quarter"]:
        wanted_periodicity = "yillik"

    q_lower = parsed["core_search"].lower()
    best_score = -1.0
    best_ind_id = None
    best_matched_core = 0

    for rank_idx, cand in enumerate(candidates[:6]):
        iid = cand["indicator_id"]
        ind_items = items_by_ind.get(iid, [])
        ind_name_norm = _normalize_for_match(cand.get("name_uz") or "")
        corpus_parts = [
            cand.get("name_uz") or "",
            cand.get("name_ru") or "",
            cand.get("name_en") or "",
        ] + [it["name_uz"] for it in ind_items]
        corpus = _normalize_for_match(" ".join(corpus_parts))

        matched_core = 0
        for tok in core_tokens:
            prefix = tok[:max(4, len(tok) - 1)] if len(tok) > 4 else tok
            if tok in corpus or prefix in corpus:
                matched_core += 1

        coverage = (matched_core / len(core_tokens)) if core_tokens else 1.0

        # Davriylik mosligi
        p_bonus = 0.0
        ind_p = (cand.get("periodicity") or "").lower()
        if wanted_periodicity and wanted_periodicity in ind_p:
            p_bonus = 0.12

        # So'ralgan yillar diapazoni qamrovi (masalan 2026 mavjudligi)
        year_bonus = 0.0
        min_y, max_y = year_bounds.get(iid, (None, None))
        if parsed["years"] and min_y and max_y:
            modern_years = [y for y in parsed["years"] if 1991 <= y <= 2026]
            if modern_years and all(min_y <= y <= max_y for y in modern_years):
                year_bonus = 0.25

        # Agregatsiya / hududiy taqsimot mosligi
        agg_bonus = 0.0
        has_1700 = any(it["item_code"] == "1700" for it in ind_items)
        if parsed["intent"] == "compare_regions":
            agg_bonus = 0.40 if len(ind_items) >= 10 else -0.40
        elif has_1700 and parsed.get("region_hint") in (None, "o'zbekiston"):
            agg_bonus = 0.18

        # Spetsifik qo'shimcha sarlavhalar jarimasi (agar foydalanuvchi so'ramagan bo'lsa)
        spec_penalty = 0.0
        if "jon boshiga" in ind_name_norm or "jonboshiga" in ind_name_norm:
            if "boshiga" not in q_lower:
                spec_penalty -= 0.25
        if ("iqtisodiy faoliyat" in ind_name_norm or "turlari bo'yicha" in ind_name_norm) and "faoliyat" not in q_lower:
            spec_penalty -= 0.15

        # RRF o'rni ustunligi
        rank_bonus = max(0.0, (6 - rank_idx) * 0.02)
        total_score = coverage * 2.0 + p_bonus + year_bonus + agg_bonus + spec_penalty + rank_bonus

        if total_score > best_score:
            best_score = total_score
            best_ind_id = iid
            best_matched_core = matched_core

    # Qat'iy mavzu chegarasi (Topic Guard):
    # Barcha asosiy predmet tokenlari topilishi kerak (yoki kamida 100% ga yaqin, chunki tuzoqlarda 1 ta begona so'z ham bo'ladi)
    if core_tokens and best_matched_core < len(core_tokens):
        return None, None, False

    # Item code ni aniqlash
    resolved_item = parsed["target_item_code"]
    ind_items = items_by_ind.get(best_ind_id, [])

    if not resolved_item and ind_items:
        # 1. Agar hudud so'ralgan bo'lsa
        r_hint = parsed.get("region_hint")
        if r_hint and r_hint != "o'zbekiston":
            for it in ind_items:
                if r_hint in _normalize_for_match(it["name_uz"]):
                    resolved_item = it["item_code"]
                    break

        # 2. Agar hudud berilmagan yoki O'zbekiston bo'lsa, hududiy ko'rsatkichlarda 1700 (Respublika) ni tanlash
        if not resolved_item:
            for it in ind_items:
                if it["item_code"] == "1700" or "o'zbekiston respublikasi" in _normalize_for_match(it["name_uz"]):
                    resolved_item = it["item_code"]
                    break

        # 3. Agar aniq tovar/klassifikator tokeni dim_item ichida bo'lsa (so'z chegarasi bilan!)
        if not resolved_item and len(ind_items) > 1:
            for it in ind_items:
                it_norm = _normalize_for_match(it["name_uz"])
                for tok in core_tokens:
                    if len(tok) >= 3 and re.search(rf"\b{re.escape(tok)}", it_norm) and "o'zbekiston" not in it_norm:
                        resolved_item = it["item_code"]
                        break
                if resolved_item:
                    break

        # 4. Agar klassifikatorda faqat 1-2 ta umumiy qator bo'lsa birinchisini olish
        if not resolved_item and len(ind_items) == 1:
            resolved_item = ind_items[0]["item_code"]

    return best_ind_id, resolved_item, True


def format_sse(event: str, data: Dict[str, Any]) -> str:
    """Server-Sent Event formatida satr shakllantiradi."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _build_deterministic_answer(
    intent: str,
    dwh_data: Dict[str, Any],
    meta_data: Dict[str, Any],
    parsed: Dict[str, Any]
) -> str:
    """DWH natijalaridan bevosita 100% verifikatsiyadan o'tadigan javob matnini quradi."""
    unit_str = meta_data.get("unit_uz") or ""
    ind_name = meta_data.get("name_uz") or "Ko'rsatkich"

    if intent == "compare_regions":
        ranking = dwh_data.get("ranking") or []
        bench = dwh_data.get("republic_benchmark")
        period = dwh_data.get("period") or ""
        valid_ranks = [r for r in ranking if r.get("value") is not None]
        if valid_ranks:
            top1 = valid_ranks[0]
            txt = (
                f"{period} holatiga ko'ra, {ind_name} bo'yicha eng yuqori ko'rsatkich "
                f"{top1['region_name']}da {top1['value']:,.1f} {unit_str}ni tashkil etgan [1]."
            )
            if bench and bench.get("value") is not None:
                txt += f" O'zbekiston Respublikasi bo'yicha umumiy qiymat {bench['value']:,.1f} {unit_str}ga teng [1]."
            return txt
        return "Ushbu davr uchun hududlar bo'yicha tasdiqlangan ma'lumot topilmadi."

    if intent == "time_series":
        timeline = [pt for pt in (dwh_data.get("timeline") or []) if pt.get("value") is not None]
        if timeline:
            item_name = dwh_data.get("item_name") or ind_name
            first_pt = timeline[0]
            last_pt = timeline[-1]
            if len(timeline) >= 2 and first_pt["period_key"] != last_pt["period_key"]:
                return (
                    f"{item_name} ({ind_name}) qiymati {first_pt['period_key']} davrida "
                    f"{first_pt['value']:,.1f} {unit_str}dan {last_pt['period_key']} davrida "
                    f"{last_pt['value']:,.1f} {unit_str}gacha o'zgardi [1]."
                )
            return (
                f"{first_pt['period_key']} holatiga ko'ra, {item_name} ko'rsatkichi "
                f"{first_pt['value']:,.1f} {unit_str}ni tashkil etgan [1]."
            )
        return "Ko'rsatilgan davrlar oralig'i uchun bazada tasdiqlangan dinamika ma'lumotlari topilmadi."

    # Default: get_data
    facts = [f for f in (dwh_data.get("data") or []) if f.get("value") is not None]
    if facts:
        if len(facts) >= 2 and len(parsed["years"]) >= 2:
            f0, f1 = facts[0], facts[-1]
            return (
                f"{f0.get('item_name', ind_name)} ko'rsatkichi {f0.get('period_key')} davrida "
                f"{f0['value']:,.1f} {unit_str}ni, {f1.get('period_key')} davrida esa "
                f"{f1['value']:,.1f} {unit_str}ni tashkil etgan [1]."
            )
        fact0 = facts[0]
        item_name = fact0.get("item_name", "ko'rsatkich")
        period_str = fact0.get("period_key", "")
        val = fact0.get("value")
        return (
            f"{period_str} holatiga ko'ra, {item_name}ning o'rtacha qiymati "
            f"{val:,.1f} {unit_str}ni tashkil etgan [1]."
        )

    raw_facts = dwh_data.get("data") or []
    if raw_facts and raw_facts[0].get("status") == "zero_marked":
        return "Ushbu davr uchun rasmiy statistik ma'lumot kiritilmagan (mavsumiy yoki nol belgilangan) [1]."
    return "Ushbu so'rov bo'yicha DWH bazasida tasdiqlangan statistik ma'lumot topilmadi."


async def orchestrate_question(question: str) -> AsyncGenerator[str, None]:
    """
    Foydalanuvchi savolini qabul qilib, 7 bosqichli SSE oqimini generatsiya qiluvchi
    asosiy asinxron orkestrator generatori.
    """
    global _gemini_consecutive_failures
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

        parsed = analyze_question_full(question)
        lang = parsed["lang"]
        search_keywords = parsed["core_search"]
        target_period = parsed["target_period"]

        yield format_sse("stage.completed", {
            "stage": "parse",
            "lang": lang,
            "normalized_query": search_keywords,
            "detected_period": target_period,
            "detected_periods": parsed["periods"],
            "detected_item_code": parsed["target_item_code"],
            "intent": parsed["intent"]
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
        search_res = tools.search_indicators(search_keywords, limit=8)
        search_dur_ms = round((time.time() - search_t0) * 1000, 2)

        selected_indicator_id, resolved_item_code, topic_valid = _select_best_candidate_and_item(
            search_res.get("results", []), parsed
        )

        yield format_sse("search.completed", {
            "stage": "search",
            "query": search_keywords,
            "execution_ms": search_dur_ms,
            "selected_indicator_id": selected_indicator_id,
            "topic_valid": topic_valid,
            "total_matches": search_res["count"],
            "results": search_res["results"][:5]
        })

        yield format_sse("stage.completed", {
            "stage": "search",
            "selected_indicator_id": selected_indicator_id
        })
        await asyncio.sleep(0.01)

        if not selected_indicator_id or not topic_valid:
            no_data_msg = "Kechirasiz, ushbu mavzu bo'yicha DWH bazasida rasmiy statistik ko'rsatkich topilmadi."
            yield format_sse("verification.completed", {
                "stage": "verify",
                "all_passed": True,
                "total_sentences": 1,
                "passed_count": 1,
                "failed_count": 0,
                "checklist": [{"text": no_data_msg, "passed": True, "reason": None, "extracted_numbers": []}]
            })
            yield format_sse("done", {
                "answer": no_data_msg,
                "sources": [],
                "all_passed": True,
                "total_duration_ms": round((time.time() - start_total_time) * 1000, 2)
            })
            return

        # =====================================================================
        # 3-BOSQICH: MCP Tool chaqiruvi (tool)
        # =====================================================================
        intent = parsed["intent"]
        avail = tools.get_available_periods(selected_indicator_id)
        avail_periods = avail.get("periods", []) if "error" not in avail else []

        # Agar foydalanuvchi aniq yillar so'ragan bo'lsa, mavjud davrlar bilan moslash
        resolved_periods: Optional[List[str]] = None
        if parsed["periods"]:
            exact_hits = [p for p in parsed["periods"] if p in avail_periods]
            if exact_hits:
                resolved_periods = exact_hits
            else:
                # Masalan, '2025' so'ralgan, lekin ko'rsatkich oylik ('2025-M01'..'2025-M12') yoki choraklik ('2025-Q3')
                prefix_hits: List[str] = []
                for req_p in parsed["periods"]:
                    matches = [ap for ap in avail_periods if ap.startswith(f"{req_p}-")]
                    if matches:
                        prefix_hits.append(matches[-1])  # Yilning eng oxirgi mavjud davri
                resolved_periods = prefix_hits if prefix_hits else parsed["periods"]

        if intent == "compare_regions" and (resolved_periods or avail_periods):
            tool_name = "compare_regions"
            cmp_period = resolved_periods[0] if resolved_periods else avail_periods[-1]
            tool_args = {"indicator_id": selected_indicator_id, "period": cmp_period}
        elif intent == "time_series" and resolved_item_code:
            tool_name = "time_series"
            tool_args = {"indicator_id": selected_indicator_id, "item_code": resolved_item_code}
        else:
            tool_name = "get_data"
            eff_periods = resolved_periods
            if not eff_periods and avail_periods:
                eff_periods = [avail_periods[-1]]
            tool_args = {
                "indicator_id": selected_indicator_id,
                "item_codes": [resolved_item_code] if resolved_item_code else None,
                "periods": eff_periods,
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
        if tool_name == "compare_regions":
            dwh_data = tools.compare_regions(
                indicator_id=tool_args["indicator_id"],
                period=tool_args["period"]
            )
            rows_count = dwh_data.get("ranking_count", 0)
        elif tool_name == "time_series":
            dwh_data = tools.time_series(
                indicator_id=tool_args["indicator_id"],
                item_code=tool_args["item_code"]
            )
            # Agar yillar oralig'i berilgan bo'lsa, timeline ni shu oraliqqa filtrlash
            if parsed["years"] and "timeline" in dwh_data:
                min_y, max_y = min(parsed["years"]), max(parsed["years"])
                filtered_tl = [
                    pt for pt in dwh_data["timeline"]
                    if pt.get("year") is not None and min_y <= pt["year"] <= max_y
                ]
                dwh_data["timeline"] = filtered_tl
                dwh_data["total_points"] = len(filtered_tl)
            rows_count = dwh_data.get("total_points", 0)
        else:
            dwh_data = tools.get_data(
                indicator_id=tool_args["indicator_id"],
                item_codes=tool_args["item_codes"],
                periods=tool_args["periods"],
                limit=tool_args["limit"]
            )
            rows_count = dwh_data.get("total_returned", 0)

        meta_data = tools.get_indicator_metadata(selected_indicator_id)
        dwh_dur_ms = round((time.time() - dwh_t0) * 1000, 2)

        yield format_sse("stage.completed", {
            "stage": "dwh",
            "table": "dwh.fact_value",
            "execution_ms": dwh_dur_ms,
            "rows_count": rows_count
        })
        await asyncio.sleep(0.01)

        # =====================================================================
        # 5-BOSQICH: Natijani taqdim etish (result)
        # =====================================================================
        result_rows = dwh_data.get("data") or dwh_data.get("timeline") or dwh_data.get("ranking") or []
        yield format_sse("tool.result", {
            "stage": "result",
            "call_id": "call_mcp_1",
            "tool": tool_name,
            "execution_ms": dwh_dur_ms,
            "table": "dwh.fact_value",
            "indicator_name": meta_data.get("name_uz"),
            "unit": meta_data.get("unit_uz"),
            "data": result_rows[:20]
        })
        await asyncio.sleep(0.01)

        # =====================================================================
        # 6-BOSQICH: Javobni generatsiya qilish (generate)
        # =====================================================================
        yield format_sse("stage.started", {
            "stage": "generate",
            "message": "Nol-gallyutsinatsiya qoidasi asosida javob shakllantirilmoqda..."
        })

        raw_llm_text = ""
        gemini_client = get_gemini_client() if _gemini_consecutive_failures < 2 else None
        gemini_succeeded = False

        if gemini_client and result_rows:
            try:
                prompt = (
                    f"Siz O'zbekiston Davlat statistika qo'mitasi rasmiy ma'lumotlar bazasi analitikasisiz.\n"
                    f"Qat'iy qoidalar:\n"
                    f"1. Har bir raqam faqat berilgan DWH natijalaridan aynan olinishi shart!\n"
                    f"2. Yangi raqam hisoblamang va taxminiy raqam kiritmang!\n"
                    f"3. Tasdiqlangan ma'lumotdan keyin [1] manba havolasi qo'ying.\n\n"
                    f"Savol: '{question}'\n"
                    f"Ko'rsatkich: {meta_data.get('name_uz')}\n"
                    f"O'lchov birligi: {meta_data.get('unit_uz')}\n"
                    f"DWH natijalari: {json.dumps(result_rows[:8], ensure_ascii=False)}\n"
                    f"O'zbek tilida lo'nda va aniq javob bering."
                )

                resp = await asyncio.wait_for(
                    asyncio.to_thread(
                        gemini_client.models.generate_content,
                        model=LLM_MODEL,
                        contents=prompt,
                        config={"temperature": 0.0}
                    ),
                    timeout=2.5
                )
                if resp and resp.text:
                    raw_llm_text = resp.text.strip()
                    gemini_succeeded = True
                    _gemini_consecutive_failures = 0
            except Exception:
                gemini_succeeded = False
                _gemini_consecutive_failures += 1

        if not gemini_succeeded or not raw_llm_text:
            raw_llm_text = _build_deterministic_answer(tool_name, dwh_data, meta_data, parsed)

        # Oqimli (streaming) delta voqealari
        words = raw_llm_text.split(" ")
        for i, word in enumerate(words):
            delta = word + (" " if i < len(words) - 1 else "")
            yield format_sse("generation.delta", {
                "stage": "generate",
                "delta": delta
            })
            await asyncio.sleep(0.005)

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
        sources = []
        if result_rows:
            snapshot_date = result_rows[0].get("snapshot_date") or "2026-11-11"
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
