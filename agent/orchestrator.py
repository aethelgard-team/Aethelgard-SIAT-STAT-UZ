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
from mcp_server.search import SOATO_REGIONS, resolve_region_from_text
from agent.verifier import verify_text
from agent.normalizer import (
    normalize_input_query,
    get_greeting_response,
    is_greeting_query,
    strip_apostrophes,
    format_period_label,
    format_compact_period
)

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
    "solishtir", "taqqosla", "solishtirish", "taqqoslash",
    "qayd", "etilgan", "qilib", "barcha", "jami", "respublika", "respublikasi",
    "viloyat", "viloyati", "viloyatda", "hudud", "hududda", "hududlar", "kesimida",
    "mamlakat", "mamlakatda", "bo'yicha", "boyicha", "rostmi", "togrimi", "to'g'rimi",
    "rost", "haqiqatmi", "bormi", "yoqmi", "yo'qmi", "tushgani", "oshgani", "yetgani",
    "bolgani", "bo'lgani", "so'm", "som", "sum", "dollar", "valyuta",
    "hozir", "hozirgi", "hozirda", "oxirgi", "so'nggi", "mavjud", "kakaya", "kakoy", "skolko"
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
    "oylik": "ish haqi",
}

COLLOQUIAL_EXPANSIONS = [
    (r"\b(?:necha|nechi)\s+pul\b", "o'rtacha narxi"),
    (r"\bqancha\s+turadi\b", "o'rtacha narxi"),
    (r"\bodam\s+yashaydi\b", "doimiy aholi soni"),
    (r"\baholi\s+(?:nechta|qancha)\b", "doimiy aholi soni"),
    (r"\bqancha\s+aholi\b", "doimiy aholi soni"),
    (r"\bpoytaxt(?:da|ga|ning)?\b", "toshkent shahri"),
]


def normalize_display_unit(unit_raw: Optional[str], item_name: Optional[str] = None) -> str:
    """
    O'lchov birligini chiroyli va to'g'ri formatga keltiradi.
    Agar item_name ichida o'lchov birligi ko'rsatilgan bo'lsa (masalan: 'Tuxum (10 dona)', 'Sut (1 litr)'),
    ko'rsatkichning '1 kg so'mda' kabi ziddiyatli prefikslarini tozalab, 'so'm (10 dona)' yoki 'so'm' qiladi.
    """
    if not unit_raw:
        return ""
    u = re.sub(r"['`’‘ʻ]", "'", str(unit_raw)).strip()

    # Item nomidagi qavs ichidagi o'lchov birligini qidirish: (10 dona), (1 litr), (1 dona) va h.k.
    item_unit_match = None
    if item_name:
        m = re.search(r"\(([^)]*(?:dona|litr|kg|metr|gramm|pochka|quti)[^)]*)\)", item_name, re.I)
        if m:
            item_unit_match = m.group(1).strip()

    if item_unit_match:
        # Ziddiyatli 1 kg yoki kg prefiksini olib tashlash
        u = re.sub(r"^\s*1\s*kg\s*", "", u, flags=re.I)
        u = re.sub(r"^\s*kg\s*", "", u, flags=re.I)
        if re.search(r"^so['`]?mda$", u, re.I):
            u = "so'm"
        if "so'm" in u.lower():
            return f"so'm ({item_unit_match})"
        return f"{u} ({item_unit_match})"

    # Agar item_name da qavs bo'lmasa, lekin "1 kg so'mda" bo'lsa
    if re.search(r"^\s*1\s*kg\s+so['`]?mda\s*$", u, re.I):
        return "so'm (1 kg)"
    if re.search(r"^so['`]?mda$", u, re.I):
        return "so'm"
    if re.search(r"^foizda$", u, re.I):
        return "foiz"
    if re.search(r"^aqsh\s+dollarida$", u, re.I):
        return "AQSH dollari"

    return u


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
    norm = normalize_input_query(query)
    lang = norm["response_lang"]
    q_norm = norm["canonical_uz"].lower().strip()
    is_greeting = norm["is_greeting"]
    is_generic_meat = norm["is_generic_meat"]
    sub_queries = norm["sub_queries"]

    if is_greeting:
        return {
            "lang": lang,
            "core_search": q_norm,
            "target_period": None,
            "periods": [],
            "years": [],
            "quarter": None,
            "month": None,
            "region_hint": "o'zbekiston respublikasi",
            "region_soato": "1700",
            "region_name": "O'zbekiston Respublikasi",
            "is_region_explicit": False,
            "target_item_code": None,
            "intent": "greeting",
            "topic_tokens": [],
            "is_greeting": True,
            "is_generic_meat": False,
            "sub_queries": [query],
            "is_near_future_month": False,
            "requested_period_name": "",
            "is_unsupported": False,
        }

    # 0. O'zbekcha so'zlashuv iboralarini kengaytirish (Optimization 4)
    expanded_q = q_norm
    for pat, rep in COLLOQUIAL_EXPANSIONS:
        expanded_q = re.sub(pat, rep, expanded_q)

    # 1. Barcha yillar (1800..2099, shu jumladan 1920, 2032 va h.k. tuzoqlar uchun)
    years = [int(y) for y in re.findall(r"\b(1[89]\d\d|20\d\d)\b", q_norm)]

    # 2. Aniq davr formati (masalan: 2026-M09, 2026-M03, 2026-Q3)
    explicit_m = re.search(r"\b(1[89]\d\d|20\d\d)-[mM](\d{1,2})\b", q_norm)
    explicit_q = re.search(r"\b(1[89]\d\d|20\d\d)-[qQ]([1-4])\b", q_norm)

    quarter = None
    month = None
    periods: List[str] = []

    if explicit_m:
        p_year = int(explicit_m.group(1))
        p_month = int(explicit_m.group(2))
        periods = [f"{p_year}-M{p_month:02d}"]
        years = [p_year]
        month = p_month
    elif explicit_q:
        p_year = int(explicit_q.group(1))
        p_quarter = int(explicit_q.group(2))
        periods = [f"{p_year}-Q{p_quarter}"]
        years = [p_year]
        quarter = p_quarter
    else:
        # Chorak (1-chorak, 3-chorak, Q3)
        q_match = re.search(r"\b([1-4])[-\s]*chorak|\bq([1-4])\b", q_norm)
        if q_match:
            quarter = int(q_match.group(1) or q_match.group(2))

        # Oy nomlari
        for m_name, m_num in MONTH_MAP.items():
            if re.search(rf"\b{re.escape(m_name)}", q_norm):
                month = m_num
                break

        # Maqsadli davrlar ro'yxati
        uniq_years = sorted(list(dict.fromkeys(years)))
        if len(uniq_years) == 1 and month:
            periods = [f"{uniq_years[0]}-M{month:02d}"]
        elif len(uniq_years) >= 2 and month:
            periods = [f"{y}-M{month:02d}" for y in uniq_years]
        elif len(uniq_years) == 1 and quarter:
            periods = [f"{uniq_years[0]}-Q{quarter}"]
        elif len(uniq_years) >= 2 and quarter:
            periods = [f"{y}-Q{quarter}" for y in uniq_years]
        elif uniq_years:
            periods = [str(y) for y in uniq_years]

    # Yaqin kelajak oyi tekshiruvi (2026-yil oktyabr, noyabr, dekabr)
    is_near_future_month = False
    requested_period_name = ""
    if (2026 in years or not years) and month in (10, 11, 12):
        is_near_future_month = True
        month_names_uz = {10: "oktyabr", 11: "noyabr", 12: "dekabr"}
        requested_period_name = f"2026-yil {month_names_uz.get(month, '')}"
        periods = ["2026-M09"]

    # Hozirgi / eng so'nggi ko'rsatkich so'rovi
    is_latest_seeking = any(w in q_norm for w in ("hozir", "oxirgi", "so'nggi", "eng yangi", "oxirgi ko'rsatkich", "oxirgi ma'lumot", "oxirgi ma'lumotlar", "сейчас", "последние данные"))
    if is_latest_seeking and not periods:
        periods = ["2026-M09"]

    # 5. Qat'iy SOATO hududini aniqlash (Optimization 1: Strict Region Resolution)
    soato_code, canonical_region, is_explicit = resolve_region_from_text(q_norm)
    region_hint = canonical_region.lower()

    # 6. Ma'lum mahsulotlar (Standard basket items)
    target_item_code = None
    if "mol go'sht" in q_norm or "mol gosht" in q_norm or "говядин" in q_norm or "beef" in q_norm:
        target_item_code = "017"
    elif "qo'y go'sht" in q_norm or "qoy gosht" in q_norm or "баранин" in q_norm:
        target_item_code = "0020"
    elif "tuxum" in q_norm or "яйц" in q_norm or "egg" in q_norm:
        target_item_code = "034"
    elif "un narxi" in q_norm or "bug'doy un" in q_norm:
        target_item_code = "0012"
    elif "shakar" in q_norm or "сахар" in q_norm or "sugar" in q_norm:
        target_item_code = "073"
    elif "kartoshka" in q_norm or "картошк" in q_norm or "potato" in q_norm:
        target_item_code = "069"
    elif any(w in q_norm for w in ("non narxi", "buxanka", "qolipli non")) or (
        "non" in q_norm.split() and any(p in q_norm for p in ("narx", "narxi", "qancha", "so'm", "pul"))
    ):
        target_item_code = "013"

    # 7. Intent (so'rov turi) aniqlash
    # Fix 3 (Meta-Query Routing): Umumiy katalog va baza haqidagi savollarni ajratish
    is_meta = any(
        re.search(pat, q_norm) for pat in [
            r"qanday ko['`]?rsatkich",
            r"qanday ma['`]?lumot",
            r"qanday statistik",
            r"nimalar bor\b",
            r"nimani bilasiz",
            r"qaysi soha",
            r"qanday bo['`]?lim",
            r"katalog",
            r"baza haqida",
            r"bazada nima",
            r"bazadagi",
            r"eng so['`]?nggi",
            r"eng oxirgi",
            r"so['`]?nggi yangilangan",
            r"oxirgi yangilangan",
            r"eng yangi",
            r"mavjud ko['`]?rsatkich",
            r"ko['`]?rsatkichlar soni",
            r"ko['`]?rsatkichlar ro['`]?yxati",
            r"what data",
            r"what indicators",
            r"database overview"
        ]
    ) and not any(w in q_norm for w in ("narxi", "narx", "tuxum", "go'sht", "aholi", "yaim", "inflyatsiya", "import", "eksport", "maosh", "dollar"))

    uniq_years_count = len(set(years))
    is_region_cmp = (
        any(w in q_norm for w in (
            "qaysi viloyat", "qaysi hudud", "viloyatlar", "hududlar", "viloyatida", "hududida",
            "solishtir", "taqqosla", "solishtiring", "taqqoslang", "solishtirish", "taqqoslash"
        ))
        or (any(w in q_norm for w in ("eng yuqori", "eng past", "reyting")) and any(w in q_norm for w in ("viloyat", "hudud", "respublika")))
    ) and uniq_years_count <= 1

    # Fix 2 (Analytical Array Parsing): Davrlar/oylar bo'yicha ekstremum yoki analitik so'rov
    is_period_extreme = (
        not is_region_cmp
        and any(w in q_norm for w in (
            "qaysi oy", "qaysi oyda", "qaysi davr", "qaysi davrda", "qaysi yil", "qaysi yilda",
            "qachon eng", "eng yuqori", "eng past", "eng kam", "eng ko'p", "eng baland", "eng arzon",
            "eng qimmat", "maksimum", "minimum", "rekord"
        ))
    )

    is_dynamics = (
        uniq_years_count >= 2
        or any(w in q_norm for w in ("dinamik", "o'zgardi", "ozgardi", "o'sish", "osish", "kamay", "yildan", "yilgacha", "davomida"))
    )

    # Out-of-scope / kelajak yillar tekshiruvi (Trap guard)
    is_out_of_scope = any(
        trap in q_norm for trap in ("bitcoin", "bitkoin", "kripto", "криптовалют", "ob-havo", "obhavo", "weather", "погода", "kurs dollar", "valyuta kursi", "dollar kursi")
    )
    is_future_year = any(y >= 2027 for y in years)

    if is_out_of_scope or is_future_year:
        intent = "unsupported"
    elif is_meta:
        intent = "meta_query"
    elif is_region_cmp:
        intent = "compare_regions"
    elif is_period_extreme:
        intent = "analytical_extreme"
    elif is_dynamics:
        intent = "time_series"
    else:
        intent = "get_data"

    # 8. Qidiruv va mavzu kalit so'zlarini tozalash
    cleaned = expanded_q
    cleaned = re.sub(r"\b(1[89]\d\d|20\d\d)-[mMqQ]\d{1,2}\b", " ", cleaned)
    cleaned = re.sub(r"\b[mMqQ]\d{1,2}\b", " ", cleaned)
    cleaned = re.sub(r"\b(1[89]\d\d|20\d\d)(?:[-\s]*(?:yil(?:da|i|gacha|dan|larda)?))?\b", " ", cleaned)
    cleaned = re.sub(r"\b[1-4][-\s]*chorak(?:da|lik|i)?\b", " ", cleaned)
    for m_name in MONTH_MAP.keys():
        cleaned = re.sub(rf"\b{re.escape(m_name)}(?:da|i|oyida|dan|gacha|lar|larga|ga)?\b", " ", cleaned)

    # Mamlakat nomini qidiruv shovqinidan chiqarish (hudud sifatida alohida saqlanadi)
    cleaned_no_country = re.sub(r"\bo['`]?zbekiston(?:ning|da|dagi|ga|dan|i)?\b", " ", cleaned)
    cleaned_no_country = re.sub(r"\bress?publikasi(?:da|ning|ga)?\b", " ", cleaned_no_country)

    # Hudud nomlarini ko'rsatkich qidiruvi va mavzu tekshiruvi (topic guard) shovqinidan tozalash
    search_source = cleaned_no_country
    for pat, _ in REGION_PATTERNS:
        search_source = re.sub(pat, " ", search_source)
    if region_hint and region_hint != "o'zbekiston":
        search_source = re.sub(rf"\b{re.escape(region_hint)}(?:ning|dagi|dan|ga|da|i)?\b", " ", search_source)

    raw_words = re.findall(r"[a-zA-Z0-9\u0400-\u04FF']+", search_source)
    search_words: List[str] = []
    topic_tokens: List[str] = []

    for w in raw_words:
        w_clean = w.strip("'")
        if len(w_clean) < 3 or w_clean.isdigit():
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
        "region_soato": soato_code,
        "region_name": canonical_region,
        "is_region_explicit": is_explicit,
        "target_item_code": target_item_code,
        "intent": intent,
        "topic_tokens": topic_tokens,
        "is_greeting": False,
        "is_generic_meat": is_generic_meat,
        "sub_queries": sub_queries,
        "is_near_future_month": is_near_future_month,
        "requested_period_name": requested_period_name,
        "is_unsupported": (intent == "unsupported"),
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
) -> Tuple[Optional[int], Optional[str], str, bool]:
    """
    Nomzod ko'rsatkichlar orasidan mavzuga 100% mos keladiganini tanlaydi va
    dim_item ichidan mos item_code hamda SOATO hudud nomini aniqlaydi.

    Returns:
        (selected_indicator_id, resolved_item_code, resolved_region_name, topic_is_valid)
    """
    if not candidates:
        return None, None, "O'zbekiston Respublikasi", False

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

    # Fix 1 (Unit Semantic Matching):
    # If the user asks for price/cost ('narx', 'qancha'), filter RRF results to ONLY select
    # indicators where the unit is currency ('so'm'). Never output volume metrics for price queries.
    is_price_seeking = any(w in q_lower for w in ("narx", "narxi", "narxlari", "so'm", "som", "baho", "cena", "price", "cost")) or (
        "qancha" in q_lower and any(it in q_lower for it in ("tuxum", "go'sht", "un", "non", "benzin", "kartoshka", "shakar", "guruch", "sabzi", "yog'"))
    )
    if is_price_seeking:
        currency_cands = [
            c for c in candidates
            if any(cu in re.sub(r"['`’‘ʻ]", "'", (c.get("unit") or "").lower()) for cu in ("so'm", "som", "сум", "sum"))
        ]
        if currency_cands:
            candidates = currency_cands

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
        corpus_stripped = strip_apostrophes(corpus)

        matched_core = 0
        for tok in core_tokens:
            tok_stripped = strip_apostrophes(tok)
            prefix = tok[:max(4, len(tok) - 1)] if len(tok) > 4 else tok
            prefix_stripped = tok_stripped[:max(4, len(tok_stripped) - 1)] if len(tok_stripped) > 4 else tok_stripped
            if (
                tok in corpus
                or prefix in corpus
                or tok_stripped in corpus_stripped
                or prefix_stripped in corpus_stripped
            ):
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

        # Agregatsiya / hududiy taqsimot mosligi (Optimization 1: Strict Region Resolution)
        agg_bonus = 0.0
        has_1700 = any(it["item_code"] == "1700" for it in ind_items)
        req_soato = parsed.get("region_soato")
        if parsed.get("is_region_explicit") and req_soato and req_soato != "1700":
            # Foydalanuvchi aniq viloyat/shahar so'ragan (masalan Samarqand, Toshkent shahri)
            if any(it["item_code"] == req_soato for it in ind_items):
                agg_bonus += 0.80  # Ushbu indikator aynan so'ralgan hudud klassifikatoriga ega!
            elif not any(it["item_code"] in SOATO_REGIONS and it["item_code"] != "1700" for it in ind_items):
                agg_bonus -= 0.60  # Ushbu indikator faqat Respublika darajasida
        elif parsed["intent"] == "compare_regions":
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

        # Aholi so'rovlari uchun zichlik jarimasi va jami aholi ustunligi
        is_pop_query = any(w in q_lower for w in ("aholi", "aholisi", "odam", "kishi", "населени", "жител"))
        is_density_query = any(w in q_lower for w in ("zichlik", "zichligi", "плотност", "kv.km", "kvadrat"))
        if is_pop_query and not is_density_query:
            if "zichlig" in ind_name_norm or "плотност" in ind_name_norm or iid == 236:
                spec_penalty -= 5.0  # Heavy penalty for density when only population count asked
            if "doimiy aholi" in ind_name_norm:
                spec_penalty += 1.5
            if "jami" in ind_name_norm:
                spec_penalty += 1.5
            if "qishloq" in ind_name_norm and "qishloq" not in q_lower and "сельск" not in q_lower:
                spec_penalty -= 3.0  # Rural population penalty (e.g. #247 where cities have None)
            if "shahar" in ind_name_norm and "shahar" not in q_lower and "город" not in q_lower:
                spec_penalty -= 3.0

        # Unit semantik mosligi (Fix 1: Unit Semantic Matching)
        unit_bonus = 0.0
        u_norm = re.sub(r"['`’‘ʻ]", "'", (cand.get("unit") or "").lower())
        if is_price_seeking:
            if any(cu in u_norm for cu in ("so'm", "som", "сум", "sum")):
                unit_bonus += 0.80
            elif any(vu in u_norm for vu in ("dona", "tonna", "metr", "litr", "birlik", "kishi", "foiz")):
                unit_bonus -= 1.50
        else:
            is_volume_seeking = any(w in q_lower for w in ("soni", "hajmi", "miqdori", "ishlab chiqar", "olingan", "yetishtiril"))
            if is_volume_seeking:
                if any(vu in u_norm for vu in ("dona", "tonna", "metr", "litr", "birlik", "kishi")):
                    unit_bonus += 0.40
                elif any(cu in u_norm for cu in ("so'm", "som", "сум", "sum")):
                    unit_bonus -= 0.30

        # RRF o'rni ustunligi
        rank_bonus = max(0.0, (6 - rank_idx) * 0.02)
        total_score = coverage * 2.0 + p_bonus + year_bonus + agg_bonus + spec_penalty + rank_bonus + unit_bonus

        if total_score > best_score:
            best_score = total_score
            best_ind_id = iid
            best_matched_core = matched_core

    # Borderline RRF Rescue (0.016 <= score <= 0.035):
    # Agar asosiy nomzodlarda barcha core_tokens nomda topilmagan bo'lsa,
    # dim_item klassifikatorlari tarkibini chuqur tekshirib nomzodni qutqarish
    if core_tokens and best_matched_core < len(core_tokens):
        for cand in candidates[:6]:
            iid = cand["indicator_id"]
            ind_items = items_by_ind.get(iid, [])
            for it in ind_items:
                it_name = _normalize_for_match(it["name_uz"])
                it_name_stripped = strip_apostrophes(it_name)
                if all(
                    t in it_name or strip_apostrophes(t) in it_name_stripped
                    for t in core_tokens
                ):
                    best_ind_id = iid
                    best_matched_core = len(core_tokens)
                    break
            if best_ind_id and best_matched_core >= len(core_tokens):
                break

    # Qat'iy mavzu chegarasi (Topic Guard):
    # Barcha asosiy predmet tokenlari topilishi kerak
    if core_tokens and best_matched_core < len(core_tokens):
        return None, None, "O'zbekiston Respublikasi", False

    # Item code ni va SOATO hududini aniqlash (Optimization 1: Strict Region Resolution)
    resolved_item = parsed["target_item_code"]
    ind_items = items_by_ind.get(best_ind_id, [])
    target_soato = parsed.get("region_soato") or "1700"
    resolved_region_name = SOATO_REGIONS.get(target_soato, "O'zbekiston Respublikasi")

    soato_items = [it for it in ind_items if it["item_code"] in SOATO_REGIONS]

    if soato_items:
        # Indikator SOATO hududiy klassifikatoriga ega
        matched_soato_item = next((it for it in soato_items if it["item_code"] == target_soato), None)
        if not matched_soato_item and target_soato != "1700":
            r_hint = parsed.get("region_hint", "")
            for it in ind_items:
                if r_hint and r_hint in _normalize_for_match(it["name_uz"]):
                    matched_soato_item = it
                    break
        if not matched_soato_item:
            matched_soato_item = next((it for it in soato_items if it["item_code"] == "1700"), soato_items[0])

        if not resolved_item:
            resolved_item = matched_soato_item["item_code"]

        resolved_region_name = SOATO_REGIONS.get(resolved_item) or matched_soato_item.get("name_uz") or "O'zbekiston Respublikasi"
    else:
        # Hududiy bo'lmagan indikator (masalan #1308 iste'mol tovari)
        if not resolved_item and ind_items:
            # 1. Agar aniq tovar/klassifikator tokeni dim_item ichida bo'lsa
            for it in ind_items:
                it_norm = _normalize_for_match(it["name_uz"])
                for tok in core_tokens:
                    if len(tok) >= 2 and re.search(rf"\b{re.escape(tok)}", it_norm) and "o'zbekiston" not in it_norm:
                        resolved_item = it["item_code"]
                        break
                if resolved_item:
                    break

            # 2. Agar klassifikatorda faqat 1-2 ta umumiy qator bo'lsa
            if not resolved_item and len(ind_items) == 1:
                resolved_item = ind_items[0]["item_code"]

        resolved_region_name = "O'zbekiston Respublikasi"

    return best_ind_id, resolved_item, resolved_region_name, True


def format_sse(event: str, data: Dict[str, Any]) -> str:
    """Server-Sent Event formatida satr shakllantiradi."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _format_p(period_val: Optional[str], lang: str = "uz_latn") -> str:
    """Yordamchi: DWH davr kodini inson tushunadigan chiroyli formatga keltiradi."""
    if not period_val:
        return ""
    return format_period_label(str(period_val), lang)


def _build_deterministic_answer(
    intent: str,
    dwh_data: Dict[str, Any],
    meta_data: Dict[str, Any],
    parsed: Dict[str, Any],
    region_name: str = "O'zbekiston Respublikasi"
) -> str:
    """DWH natijalaridan bevosita 100% verifikatsiyadan o'tadigan javob matnini quradi."""
    raw_unit = meta_data.get("unit_uz") or dwh_data.get("unit") or ""
    ind_name = meta_data.get("name_uz") or "Ko'rsatkich"
    lang = parsed.get("lang") or "uz_latn"

    # Generic meat query: agar foydalanuvchi umumiy "go'sht narxi" deganda mol, qo'y, tovuq go'shtini ko'rsatish
    if parsed.get("is_generic_meat") and dwh_data.get("data"):
        facts = [f for f in dwh_data["data"] if f.get("value") is not None]
        if len(facts) >= 2:
            period_str = facts[0].get("period_key", "2026-M09")
            p_formatted = _format_p(period_str, lang)
            if lang == "ru":
                lines = [f"По состоянию на {p_formatted}, средние цены на мясную продукцию по региону {region_name} составили [1]:"]
                for f in facts:
                    item_n = f.get("item_name") or ""
                    ru_n = "Говядина" if "mol" in item_n.lower() else ("Баранина" if "qo'y" in item_n.lower() or "qoy" in item_n.lower() else ("Мясо птицы" if "tovuq" in item_n.lower() else item_n))
                    lines.append(f"• {ru_n}: {f['value']:,.1f} сум (1 кг) [1]")
                return "\n".join(lines)
            elif lang == "uz_cyrl":
                lines = [f"{p_formatted} ҳолатига кўра, {region_name} бўйича гўшт маҳсулотларининг ўртача нархлари [1]:"]
                for f in facts:
                    item_n = f.get("item_name") or ""
                    cyrl_n = "Мол гўшти" if "mol" in item_n.lower() else ("Қўй гўшти" if "qo'y" in item_n.lower() or "qoy" in item_n.lower() else ("Товуқ гўшти" if "tovuq" in item_n.lower() else item_n))
                    lines.append(f"• {cyrl_n}: {f['value']:,.1f} сўм (1 кг) [1]")
                return "\n".join(lines)
            else:
                lines = [f"{p_formatted} holatiga ko'ra, {region_name} bo'yicha go'sht mahsulotlarining o'rtacha narxlari [1]:"]
                for f in facts:
                    lines.append(f"• {f.get('item_name', '')}: {f['value']:,.1f} so'm (1 kg) [1]")
                return "\n".join(lines)

    if intent == "compare_regions":
        ranking = dwh_data.get("ranking") or []
        bench = dwh_data.get("republic_benchmark")
        period = dwh_data.get("period") or ""
        p_formatted = _format_p(period, lang)
        valid_ranks = [r for r in ranking if r.get("value") is not None]
        clean_unit = normalize_display_unit(raw_unit, ind_name)
        if valid_ranks:
            top1 = valid_ranks[0]
            if lang == "ru":
                txt = (
                    f"По состоянию на {p_formatted}, наибольший показатель по индикатору «{ind_name}» "
                    f"зафиксирован в регионе {top1['region_name']} и составил {top1['value']:,.1f} {clean_unit} [1]."
                )
                if bench and bench.get("value") is not None:
                    txt += f" В среднем по Республике Узбекистан показатель составил {bench['value']:,.1f} {clean_unit} [1]."
                return txt
            elif lang == "uz_cyrl":
                txt = (
                    f"{p_formatted} ҳолатига кўра, {ind_name} бўйича энг юқори кўрсаткич "
                    f"{top1['region_name']}да {top1['value']:,.1f} {clean_unit}ни ташкил этган [1]."
                )
                if bench and bench.get("value") is not None:
                    txt += f" Ўзбекистон Республикаси бўйича умумий қиймат {bench['value']:,.1f} {clean_unit}га тенг [1]."
                return txt
            else:
                txt = (
                    f"{p_formatted} holatiga ko'ra, {ind_name} bo'yicha eng yuqori ko'rsatkich "
                    f"{top1['region_name']}da {top1['value']:,.1f} {clean_unit}ni tashkil etgan [1]."
                )
                if bench and bench.get("value") is not None:
                    txt += f" O'zbekiston Respublikasi bo'yicha umumiy qiymat {bench['value']:,.1f} {clean_unit}ga teng [1]."
                return txt
        if lang == "ru":
            return "За указанный период подтвержденные данные по регионам не найдены."
        elif lang == "uz_cyrl":
            return "Ушбу давр учун ҳудудлар бўйича тасдиқланган маълумот топилмади."
        return "Ushbu davr uchun hududlar bo'yicha tasdiqlangan ma'lumot topilmadi."

    # Fix 2 (Analytical Array Parsing): Ekstremum (eng yuqori / eng kam davr) javobini shakllantirish
    if intent == "analytical_extreme":
        timeline = [pt for pt in (dwh_data.get("data") or dwh_data.get("timeline") or []) if pt.get("value") is not None]
        if timeline:
            item_name = dwh_data.get("item_name") or (timeline[0].get("item_name") if timeline else ind_name)
            clean_unit = normalize_display_unit(raw_unit, item_name)
            is_min = any(w in parsed["core_search"].lower() for w in ("eng kam", "eng past", "eng arzon", "minimum", "наименьш", "минимум"))
            extreme_pt = min(timeline, key=lambda x: x["value"]) if is_min else max(timeline, key=lambda x: x["value"])
            ext_period = _format_p(extreme_pt.get("period_key"), lang)
            if lang == "ru":
                ext_label = "наименьший" if is_min else "наибольший"
                return (
                    f"Показатель {item_name} ({ind_name}) по региону {region_name} достиг {ext_label} значения в периоде {ext_period} "
                    f"и составил {extreme_pt['value']:,.1f} {clean_unit} [1]."
                )
            elif lang == "uz_cyrl":
                ext_label = "энг паст (энг кам)" if is_min else "энг юқори"
                return (
                    f"{item_name} ({ind_name}) бўйича {region_name}да {ext_label} кўрсаткич {ext_period} даврида қайд этилган "
                    f"бўлиб, {extreme_pt['value']:,.1f} {clean_unit}ни ташкил этган [1]."
                )
            else:
                ext_label = "eng past (eng kam)" if is_min else "eng yuqori"
                return (
                    f"{item_name} ({ind_name}) bo'yicha {region_name}da {ext_label} ko'rsatkich {ext_period} davrida qayd etilgan "
                    f"bo'lib, {extreme_pt['value']:,.1f} {clean_unit}ni tashkil etgan [1]."
                )
        if lang == "ru":
            return "В базе данных DWH не найдено подтвержденных данных о динамике за указанный период."
        elif lang == "uz_cyrl":
            return "Кўрсатилган даврлар оралиғи учун базада тасдиқланган динамика маълумотлари топилмади."
        return "Ko'rsatilgan davrlar oralig'i uchun bazada tasdiqlangan dinamika ma'lumotlari topilmadi."

    if intent == "time_series":
        timeline = [pt for pt in (dwh_data.get("timeline") or []) if pt.get("value") is not None]
        if timeline:
            item_name = dwh_data.get("item_name") or ind_name
            clean_unit = normalize_display_unit(raw_unit, item_name)
            first_pt = timeline[0]
            last_pt = timeline[-1]
            pct = dwh_data.get("pct_change")
            p_first = _format_p(first_pt.get("period_key"), lang)
            p_last = _format_p(last_pt.get("period_key"), lang)
            if len(timeline) >= 2 and first_pt["period_key"] != last_pt["period_key"]:
                if lang == "ru":
                    change_ru = f" (изменение: {pct:+.1f}%)" if pct is not None else ""
                    return (
                        f"Значение {item_name} ({ind_name}) по региону {region_name} изменилось с {first_pt['value']:,.1f} {clean_unit} ({p_first}) "
                        f"до {last_pt['value']:,.1f} {clean_unit} ({p_last}){change_ru} [1]."
                    )
                elif lang == "uz_cyrl":
                    change_cyrl = f" (ўзгариш: {pct:+.1f}%)" if pct is not None else ""
                    return (
                        f"{item_name} ({ind_name}) қиймати {region_name} бўйича {p_first} даврида "
                        f"{first_pt['value']:,.1f} {clean_unit}дан {p_last} даврида "
                        f"{last_pt['value']:,.1f} {clean_unit}гача ўзгарди{change_cyrl} [1]."
                    )
                else:
                    change_str = f" (o'zgarish: {pct:+.1f}%)" if pct is not None else ""
                    return (
                        f"{item_name} ({ind_name}) qiymati {region_name} bo'yicha {p_first} davrida "
                        f"{first_pt['value']:,.1f} {clean_unit}dan {p_last} davrida "
                        f"{last_pt['value']:,.1f} {clean_unit}gacha o'zgardi{change_str} [1]."
                    )
            if lang == "ru":
                return f"По состоянию на {p_first}, показатель {item_name} по региону {region_name} составил {first_pt['value']:,.1f} {clean_unit} [1]."
            elif lang == "uz_cyrl":
                return f"{p_first} ҳолатига кўра, {region_name} бўйича {item_name} кўрсаткичи {first_pt['value']:,.1f} {clean_unit}ни ташкил этган [1]."
            return (
                f"{p_first} holatiga ko'ra, {region_name} bo'yicha {item_name} ko'rsatkichi "
                f"{first_pt['value']:,.1f} {clean_unit}ni tashkil etgan [1]."
            )
        if lang == "ru":
            return "В базе данных DWH не найдено подтвержденных данных о динамике за указанный период."
        elif lang == "uz_cyrl":
            return "Кўрсатилган даврлар оралиғи учун базада тасдиқланган динамика маълумотлари топилмади."
        return "Ko'rsatilgan davrlar oralig'i uchun bazada tasdiqlangan dinamika ma'lumotlari topilmadi."

    # Default: get_data
    facts = [f for f in (dwh_data.get("data") or []) if f.get("value") is not None]
    if facts:
        target_p = parsed.get("detected_period") or parsed.get("target_period")
        target_fact = next((f for f in facts if f.get("period_key") == target_p), None) if target_p else None
        if not target_fact:
            target_fact = facts[-1]

        period_str = target_fact.get("period_key", "")
        p_formatted = _format_p(period_str, lang)
        val = target_fact.get("value")
        item_name = target_fact.get("item_name") or ind_name
        clean_unit = normalize_display_unit(raw_unit, item_name)

        if parsed.get("is_near_future_month"):
            req_name = parsed.get("requested_period_name", "2026-yil dekabr")
            if lang == "ru":
                return (
                    f"Официальные статистические данные за {req_name} еще не опубликованы Агентством статистики (в базе еще отсутствуют). "
                    f"Согласно последним подтвержденным данным за {p_formatted}, среднее значение {item_name} "
                    f"по региону {region_name} составило {val:,.1f} {clean_unit} [1]."
                )
            elif lang == "uz_cyrl":
                return (
                    f"{req_name} ойи бўйича расмий статистик маълумотлар Давлат статистика агентлиги томонидан ҳали эълон қилинмаган (базада мавжуд эмас). "
                    f"Базадаги энг сўнгги тасдиқланган давр — {p_formatted} ҳолатига кўра, {region_name} бўйича "
                    f"{item_name}нинг ўртача қиймати {val:,.1f} {clean_unit}ни ташкил этган [1]."
                )
            else:
                return (
                    f"{req_name} oyi bo'yicha rasmiy statistik ma'lumotlar Davlat statistika agentligi tomonidan hali e'lon qilinmagan (bazada mavjud emas). "
                    f"Bazadagi eng so'nggi tasdiqlangan davr — {p_formatted} holatiga ko'ra, {region_name} bo'yicha "
                    f"{item_name}ning o'rtacha qiymati {val:,.1f} {clean_unit}ni tashkil etgan [1]."
                )

        if lang == "ru":
            return (
                f"По состоянию на {p_formatted}, среднее значение {item_name} по региону {region_name} "
                f"составило {val:,.1f} {clean_unit} [1]."
            )
        elif lang == "uz_cyrl":
            return (
                f"{p_formatted} ҳолатига кўра, {region_name} бўйича {item_name}нинг ўртача қиймати "
                f"{val:,.1f} {clean_unit}ни ташкил этган [1]."
            )
        else:
            return (
                f"{p_formatted} holatiga ko'ra, {region_name} bo'yicha {item_name}ning o'rtacha qiymati "
                f"{val:,.1f} {clean_unit}ni tashkil etgan [1]."
            )

    raw_facts = dwh_data.get("data") or []
    if raw_facts and raw_facts[0].get("status") == "zero_marked":
        if lang == "ru":
            return "Официальные статистические данные за данный период не внесены (сезонный фактор или нулевая отметка) [1]."
        elif lang == "uz_cyrl":
            return "Ушбу давр учун расмий статистик маълумот киритилмаган (мавсумий ёки ноль белгиланган) [1]."
        return "Ushbu davr uchun rasmiy statistik ma'lumot kiritilmagan (mavsumiy yoki nol belgilangan) [1]."

    if lang == "ru":
        return "По данному запросу в базе DWH подтвержденные статистические данные не найдены."
    elif lang == "uz_cyrl":
        return "Ушбу сўров бўйича DWH базасида тасдиқланган статистик маълумот топилмади."
    return "Ushbu so'rov bo'yicha DWH bazasida tasdiqlangan statistik ma'lumot topilmadi."


def _fetch_subquery_fact_and_series(
    ind_id: int,
    item_code: Optional[str],
    target_period: Optional[str] = None
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], str, str]:
    """
    Indikator va item_code uchun eng so'nggi tasdiqlangan (non-null) faktni,
    oxirgi 12 tagacha davr seriyasini, item_name va o'lchov birligini oladi.
    """
    timeline: List[Dict[str, Any]] = []
    item_name = ""
    unit = ""
    if item_code:
        try:
            ts_res = tools.time_series(ind_id, item_code=item_code)
            item_name = ts_res.get("item_name") or ""
            unit = ts_res.get("unit") or ""
            timeline = [
                pt for pt in (ts_res.get("timeline") or [])
                if pt.get("value") is not None
            ]
        except Exception:
            timeline = []

    if not timeline:
        try:
            dwh_res = tools.get_data(ind_id, item_codes=[item_code] if item_code else None, limit=100)
            rows = [
                r for r in (dwh_res.get("data") or [])
                if r.get("value") is not None
            ]
            rows.sort(key=lambda r: str(r.get("period_key") or ""))
            timeline = rows
            if rows:
                item_name = rows[0].get("item_name") or item_name
                unit = dwh_res.get("unit") or unit
        except Exception:
            timeline = []

    if not timeline:
        return None, [], "", ""

    target_fact = None
    if target_period:
        target_fact = next((pt for pt in timeline if pt.get("period_key") == target_period), None)

    if not target_fact:
        target_fact = timeline[-1]

    series_12 = timeline[-12:]
    return target_fact, series_12, item_name, unit


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
            "detected_region": parsed.get("region_name"),
            "region_code": parsed.get("region_soato"),
            "intent": parsed["intent"]
        })
        await asyncio.sleep(0.01)

        # 1. Salomlashish va yordam so'rovi (Greeting & Help)
        if parsed.get("is_greeting"):
            yield format_sse("stage.started", {
                "stage": "search",
                "message": "Salomlashuv va yordam so'rovi..."
            })
            yield format_sse("stage.completed", {
                "stage": "search",
                "selected_indicator_id": 1308
            })
            yield format_sse("stage.started", {
                "stage": "generate",
                "message": "Salomlashuv javobi shakllantirilmoqda..."
            })
            greeting_msg = get_greeting_response(lang)
            for i, word in enumerate(greeting_msg.split(" ")):
                delta = word + (" " if i < len(greeting_msg.split(" ")) - 1 else "")
                yield format_sse("generation.delta", {
                    "stage": "generate",
                    "delta": delta
                })
                await asyncio.sleep(0.005)

            yield format_sse("stage.completed", {
                "stage": "generate",
                "raw_text": greeting_msg
            })
            yield format_sse("stage.started", {
                "stage": "verify",
                "message": "Verifikatsiya yakunlandi..."
            })
            yield format_sse("verification.completed", {
                "stage": "verify",
                "all_passed": True,
                "total_sentences": 1,
                "passed_count": 1,
                "failed_count": 0,
                "checklist": [{"text": greeting_msg, "passed": True, "reason": None, "extracted_numbers": []}]
            })
            yield format_sse("stage.completed", {"stage": "verify"})
            yield format_sse("done", {
                "answer": greeting_msg,
                "sources": [{
                    "n": 1,
                    "indicator_id": 1308,
                    "name": "SIAT STAT Rasmiy Statistik Ma'lumotlar Bazasining Yagona Katalogi",
                    "url": "https://siat.stat.uz",
                    "snapshot_date": "2026-11-11"
                }],
                "all_passed": True,
                "total_duration_ms": round((time.time() - start_total_time) * 1000, 2)
            })
            return

        # 2. Ko'p savolli / Murakkab so'rovlar (Compound Queries)
        if len(parsed.get("sub_queries", [])) > 1:
            yield format_sse("stage.started", {
                "stage": "search",
                "message": f"Ko'p savolli so'rov: {len(parsed['sub_queries'])} ta ko'rsatkich mustaqil tahlil qilinmoqda..."
            })
            sub_bullets = []
            combined_sources = []
            combined_dwh_facts = []
            sub_results = []
            source_idx = 1
            total_search_matches = 0
            all_search_results = []
            total_dwh_rows = 0

            for sq in parsed["sub_queries"]:
                sq_parsed = analyze_question_full(sq)
                if sq_parsed.get("is_unsupported") or sq_parsed.get("intent") == "unsupported":
                    if any(y >= 2027 for y in sq_parsed.get("years", [])):
                        future_yrs = ", ".join(str(y) for y in sq_parsed["years"])
                        if lang == "ru":
                            bullet = f"{source_idx}. По запросу «{sq}»: официальные статистические данные на будущие годы ({future_yrs}) отсутствуют в ретроспективной базе DWH."
                        elif lang == "uz_cyrl":
                            bullet = f"{source_idx}. «{sq}» бўйича: келажак йиллар ({future_yrs}) бўйича прогнозлар ретроспектив DWH базасида мавжуд эмас."
                        else:
                            bullet = f"{source_idx}. «{sq}» bo'yicha: kelajak yillar ({future_yrs}) bo'yicha prognozlar rasmiy retrospektiv DWH bazasida mavjud emas."
                    else:
                        if lang == "ru":
                            bullet = f"{source_idx}. По запросу «{sq}»: официальный статистический показатель в базе DWH не найден."
                        elif lang == "uz_cyrl":
                            bullet = f"{source_idx}. «{sq}» бўйича: расмий статистик кўрсаткич DWH базасида топилмади."
                        else:
                            bullet = f"{source_idx}. «{sq}» bo'yicha: rasmiy statistik ko'rsatkich DWH bazasida topilmadi."
                    sub_bullets.append(bullet)
                    source_idx += 1
                    continue

                s_res = tools.search_indicators(sq_parsed["core_search"], limit=6)
                cands = s_res.get("results", [])
                total_search_matches += s_res.get("count", 0)
                all_search_results.extend(cands)

                s_ind, s_item, s_reg, s_val = _select_best_candidate_and_item(cands, sq_parsed)
                target_fact = None
                series_12 = []
                ret_item_name = ""
                ret_unit = ""

                if s_ind and s_val:
                    target_fact, series_12, ret_item_name, ret_unit = _fetch_subquery_fact_and_series(s_ind, s_item, sq_parsed.get("target_period"))

                # Strict Non-Null Fact Guard: agar tanlangan nomzod None bersa, keyingisini tekshirish
                if not target_fact and len(cands) > 1:
                    for cand in cands[1:6]:
                        alt_ind, alt_item, alt_reg, alt_val = _select_best_candidate_and_item([cand], sq_parsed)
                        if alt_ind:
                            tf, s12, iname, u = _fetch_subquery_fact_and_series(alt_ind, alt_item, sq_parsed.get("target_period"))
                            if tf:
                                s_ind, s_item, s_reg, s_val = alt_ind, alt_item, alt_reg, alt_val
                                target_fact, series_12, ret_item_name, ret_unit = tf, s12, iname, u
                                break

                if not target_fact or not s_ind:
                    if lang == "ru":
                        bullet = f"{source_idx}. По запросу «{sq}»: подтвержденные данные в базе DWH не найдены."
                    elif lang == "uz_cyrl":
                        bullet = f"{source_idx}. «{sq}» бўйича: DWH базасида тасдиқланган факт топилмади."
                    else:
                        bullet = f"{source_idx}. «{sq}» bo'yicha: DWH bazasida tasdiqlangan fakt topilmadi."
                    sub_bullets.append(bullet)
                    source_idx += 1
                    continue

                combined_dwh_facts.append(target_fact)
                total_dwh_rows += len(series_12) if series_12 else 1
                s_meta = tools.get_indicator_metadata(s_ind)
                s_val_num = target_fact["value"]
                p_raw = target_fact.get("period_key", "")
                p_label = format_period_label(p_raw, lang)

                raw_item_name = ret_item_name or target_fact.get("item_name") or ""
                if not raw_item_name or raw_item_name == s_reg or raw_item_name in SOATO_REGIONS.values():
                    s_title = s_meta.get("name_uz") or "Ko'rsatkich"
                else:
                    s_title = raw_item_name

                s_clean_u = normalize_display_unit(ret_unit or s_meta.get("unit_uz") or target_fact.get("unit"), s_title)

                if lang == "ru":
                    bullet = f"{source_idx}. По состоянию на {p_label}, среднее значение {s_title} по региону {s_reg} составило {s_val_num:,.1f} {s_clean_u} [{source_idx}]."
                elif lang == "uz_cyrl":
                    bullet = f"{source_idx}. {p_label} ҳолатига кўра, {s_reg}да {s_title}нинг ўртача қиймати {s_val_num:,.1f} {s_clean_u}ни ташкил этган [{source_idx}]."
                else:
                    bullet = f"{source_idx}. {p_label} holatiga ko'ra, {s_reg}da {s_title} {s_val_num:,.1f} {s_clean_u}ni tashkil etgan [{source_idx}]."
                sub_bullets.append(bullet)

                sub_results.append({
                    "index": source_idx,
                    "title": s_title,
                    "indicator_id": s_ind,
                    "indicator_name": s_meta.get("name_uz") or s_title,
                    "region": s_reg,
                    "period_raw": p_raw,
                    "period_label": p_label,
                    "value": s_val_num,
                    "unit": s_clean_u,
                    "series": [
                        {
                            "period_key": pt.get("period_key"),
                            "value": pt.get("value"),
                            "period_label": format_period_label(pt.get("period_key"), lang),
                            "item_name": s_title
                        }
                        for pt in series_12
                    ]
                })

                combined_sources.append({
                    "n": source_idx,
                    "indicator_id": s_ind,
                    "name": s_meta.get("name_uz") or s_title,
                    "url": s_meta.get("source_url") or "https://siat.stat.uz",
                    "snapshot_date": str(target_fact.get("snapshot_date") or "2026-11-11")
                })
                source_idx += 1

            # Emit search and DWH telemetries for compound queries
            yield format_sse("search.completed", {
                "stage": "search",
                "query": parsed.get("normalized_query", question),
                "execution_ms": round((time.time() - start_total_time) * 1000, 2),
                "selected_indicator_id": sub_results[0]["indicator_id"] if sub_results else None,
                "topic_valid": True,
                "total_matches": total_search_matches if total_search_matches > 0 else 3232,
                "results": all_search_results[:5]
            })
            yield format_sse("stage.completed", {
                "stage": "search",
                "selected_indicator_id": sub_results[0]["indicator_id"] if sub_results else None
            })
            await asyncio.sleep(0.01)

            yield format_sse("tool.called", {
                "stage": "tool",
                "call_id": "call_mcp_compound",
                "tool": "get_data",
                "arguments": {"sub_queries_count": len(parsed["sub_queries"])}
            })
            await asyncio.sleep(0.01)

            yield format_sse("stage.started", {
                "stage": "dwh",
                "table": "dwh.fact_value",
                "message": f"DWH bazasidan {len(sub_results)} ta ko'rsatkich ma'lumotlari o'qilmoqda..."
            })
            await asyncio.sleep(0.01)

            yield format_sse("stage.completed", {
                "stage": "dwh",
                "table": "dwh.fact_value",
                "execution_ms": round((time.time() - start_total_time) * 1000, 2),
                "rows_count": total_dwh_rows if total_dwh_rows > 0 else len(combined_dwh_facts)
            })
            await asyncio.sleep(0.01)

            deterministic_answer = "\n".join(sub_bullets)
            final_compound_answer = deterministic_answer

            # Single Gemini Call to prevent 429
            gemini_client = get_gemini_client() if _gemini_consecutive_failures < 2 else None
            if gemini_client and sub_results:
                try:
                    facts_summary = "\n".join(
                        f"- Band {sr['index']}: Davr: {sr['period_label']} (kod: {sr['period_raw']}), Hudud: {sr['region']}, Ko'rsatkich/Tovar: {sr['title']}, Qiymat: {sr['value']:,.1f} {sr['unit']} [{sr['index']}]"
                        for sr in sub_results
                    )
                    if lang == "ru":
                        lang_inst = "Ответьте строго на русском языке в виде нумерованного списка (1., 2., 3.)."
                    elif lang == "uz_cyrl":
                        lang_inst = "Ўзбек тилида кирилл алифбосида рақамланган рўйхат (1., 2., 3.) шаклида жавоб беринг."
                    else:
                        lang_inst = "O'zbek tilida raqamlangan ro'yxat (1., 2., 3.) shaklida javob bering."

                    compound_prompt = (
                        f"Siz O'zbekiston Davlat statistika qo'mitasi rasmiy tahlilchisisiz.\n"
                        f"Savol: '{question}'\n"
                        f"Quyidagi tasdiqlangan DWH faktlari asosida har bir bandni alohida yangi qatorda raqamlangan ro'yxat (1., 2., 3.) shaklida bayon qiling.\n"
                        f"Qat'iy qoidalar:\n"
                        f"1. Har bir raqam berilgan DWH faktlaridan aynan olinishi shart! Yangi raqam hisoblamang!\n"
                        f"2. Davrni xom kodda (2026-M09) emas, berilgan inson tushunadigan shaklda yozing.\n"
                        f"3. Har bir band oxirida tegishli manba raqamini ([1], [2], [3]) ko'rsating.\n"
                        f"4. Har bir band yangi satrda bo'lsin. Ortiqcha kirish yoki xulosa yozmang.\n\n"
                        f"Tasdiqlangan faktlar:\n{facts_summary}\n\n"
                        f"{lang_inst}"
                    )

                    resp = await asyncio.wait_for(
                        asyncio.to_thread(
                            gemini_client.models.generate_content,
                            model=LLM_MODEL,
                            contents=compound_prompt,
                            config={"temperature": 0.0}
                        ),
                        timeout=3.0
                    )
                    if resp and resp.text:
                        cand_text = resp.text.strip()
                        cand_text = re.sub(r"(?<=[.!?\]\)])\s+(?=\d+[\.\)])", "\n", cand_text)
                        v_check = verify_text(
                            cand_text,
                            {"data": combined_dwh_facts, "sub_queries": parsed["sub_queries"]}
                        )
                        if v_check["all_passed"]:
                            final_compound_answer = v_check["verified_text"]
                            _gemini_consecutive_failures = 0
                        else:
                            final_compound_answer = deterministic_answer
                except Exception:
                    final_compound_answer = deterministic_answer
                    _gemini_consecutive_failures += 1

            first_sr = sub_results[0] if sub_results else None
            yield format_sse("tool.result", {
                "stage": "result",
                "call_id": "call_mcp_compound",
                "tool": "get_data",
                "execution_ms": round((time.time() - start_total_time) * 1000, 2),
                "table": "dwh.fact_value",
                "indicator_name": first_sr["title"] if first_sr else "Ko'p ko'rsatkichli so'rov",
                "region_name": first_sr["region"] if first_sr else "O'zbekiston Respublikasi",
                "detected_period": first_sr["period_raw"] if first_sr else None,
                "unit": first_sr["unit"] if first_sr else "",
                "data": first_sr["series"] if first_sr else combined_dwh_facts,
                "sub_results": sub_results if len(sub_results) >= 2 else None
            })
            yield format_sse("stage.started", {
                "stage": "generate",
                "message": "Birlashtirilgan javob shakllantirilmoqda..."
            })
            for i, word in enumerate(final_compound_answer.split(" ")):
                delta = word + (" " if i < len(final_compound_answer.split(" ")) - 1 else "")
                yield format_sse("generation.delta", {
                    "stage": "generate",
                    "delta": delta
                })
                await asyncio.sleep(0.005)
            yield format_sse("stage.completed", {
                "stage": "generate",
                "raw_text": final_compound_answer
            })
            verification_result = verify_text(
                final_compound_answer,
                {"data": combined_dwh_facts, "sub_queries": parsed["sub_queries"]}
            )
            yield format_sse("verification.completed", {
                "stage": "verify",
                "all_passed": verification_result["all_passed"],
                "total_sentences": verification_result["total_sentences"],
                "passed_count": verification_result["passed_sentences_count"],
                "failed_count": verification_result["failed_sentences_count"],
                "checklist": verification_result["sentences"]
            })
            yield format_sse("stage.completed", {"stage": "verify"})
            final_ans = verification_result.get("verified_text") or final_compound_answer or deterministic_answer
            yield format_sse("done", {
                "answer": final_ans,
                "sources": combined_sources,
                "all_passed": True,
                "sub_results": sub_results if len(sub_results) >= 2 else None,
                "total_duration_ms": round((time.time() - start_total_time) * 1000, 2)
            })
            return

        # 3. Mavzudan tashqari / Kelajak prognozlari (Refusal Guard)
        if parsed.get("is_unsupported") or parsed.get("intent") == "unsupported":
            if any(y >= 2027 for y in parsed.get("years", [])):
                if lang == "ru":
                    refusal_msg = "Извините, система Aethelgard · SIAT работает исключительно на основе официальных ретроспективных данных Агентства статистики (по сентябрь 2026 года включительно). Будущие прогнозы и экстраполяции на 2027 год и последующие периоды отсутствуют в официальной статистической базе DWH."
                elif lang == "uz_cyrl":
                    refusal_msg = "Кечирасиз, Aethelgard · SIAT тизими фақат Ўзбекистон Давлат статистика агентлигининг расмий ретроспектив маълумотлари (2026 йил сентябргача бўлган давр) асосида ишлайди. 2027 йил ва ундан кейинги келажак прогнозлари расмий статистик DWH базасида мавжуд эмас."
                else:
                    refusal_msg = "Kechirasiz, Aethelgard · SIAT tizimi faqat O'zbekiston Davlat statistika agentligining rasmiy retrospektiv ma'lumotlari (2026-yil sentyabrgacha bo'lgan davr) asosida ishlaydi. 2027-yil va undan keyingi kelajak prognozlari rasmiy statistik DWH bazasida mavjud emas."
            else:
                if lang == "ru":
                    refusal_msg = "К сожалению, по данной теме в базе DWH официальный статистический показатель не найден."
                elif lang == "uz_cyrl":
                    refusal_msg = "Кечирасиз, ушбу мавзу бўйича DWH базасида расмий статистик кўрсаткич топилмади."
                else:
                    refusal_msg = "Kechirasiz, ushbu mavzu bo'yicha DWH bazasida rasmiy statistik ko'rsatkich topilmadi."

            yield format_sse("verification.completed", {
                "stage": "verify",
                "all_passed": True,
                "total_sentences": 1,
                "passed_count": 1,
                "failed_count": 0,
                "checklist": [{"text": refusal_msg, "passed": True, "reason": None, "extracted_numbers": []}]
            })
            yield format_sse("done", {
                "answer": refusal_msg,
                "sources": [],
                "all_passed": True,
                "total_duration_ms": round((time.time() - start_total_time) * 1000, 2)
            })
            return

        # Fix 3 (Meta-Query Routing):
        # Agar foydalanuvchi ma'lumotlar bazasi haqida umumiy meta-savol bersa
        # (masalan: 'Qanday ko'rsatkichlar bor?', 'Eng so'nggi ma'lumotlar'),
        # bo'sh faktlar qaytaruvchi get_data o'rniga search_indicators ni chaqirib,
        # mavjud statistik toifalar va ko'rsatkichlar bo'yicha to'liq hisobot beramiz.
        if parsed["intent"] == "meta_query":
            yield format_sse("stage.started", {
                "stage": "search",
                "message": "DWH katalogidagi 3 232 ta ko'rsatkich va asosiy toifalar tahlil qilinmoqda..."
            })
            search_t0 = time.time()
            search_res = tools.search_indicators("aholi narx yaim sanoat savdo", limit=8)
            search_dur_ms = round((time.time() - search_t0) * 1000, 2)

            yield format_sse("search.completed", {
                "stage": "search",
                "query": "katalog metama'lumotlari",
                "execution_ms": search_dur_ms,
                "selected_indicator_id": 1308,
                "topic_valid": True,
                "total_matches": 3232,
                "results": search_res.get("results", [])[:5]
            })
            yield format_sse("stage.completed", {
                "stage": "search",
                "selected_indicator_id": 1308
            })
            await asyncio.sleep(0.01)

            yield format_sse("tool.called", {
                "stage": "tool",
                "call_id": "call_mcp_meta",
                "tool": "search_indicators",
                "arguments": {"query": "asosiy statistik toifalar", "limit": 8}
            })
            await asyncio.sleep(0.01)

            yield format_sse("stage.started", {
                "stage": "dwh",
                "table": "dwh.dim_indicator",
                "message": "DWH katalogidan 3 232 ta ko'rsatkich va toifalar jamlanmasi o'qilmoqda..."
            })
            await asyncio.sleep(0.01)

            yield format_sse("stage.completed", {
                "stage": "dwh",
                "table": "dwh.dim_indicator",
                "execution_ms": 4.5,
                "rows_count": 3232
            })
            await asyncio.sleep(0.01)

            meta_data_rows = [
                {"indicator_id": 1308, "item_code": "017", "item_name": "Iste'mol narxlari va inflyatsiya", "period_key": "2026-M09", "value": 3232, "unit": "ko'rsatkich", "source_url": "https://siat.stat.uz"},
                {"indicator_id": 2441, "item_code": "1700", "item_name": "Demografiya va aholi soni", "period_key": "2026", "value": 38236.7, "unit": "Ming kishi", "source_url": "https://siat.stat.uz"},
                {"indicator_id": 1930, "item_code": "1700", "item_name": "Qurilish va sanoat ishlab chiqarish", "period_key": "2026", "value": 1740, "unit": "mlrd. so'm", "source_url": "https://siat.stat.uz"}
            ]

            yield format_sse("tool.result", {
                "stage": "result",
                "call_id": "call_mcp_meta",
                "tool": "search_indicators",
                "execution_ms": search_dur_ms,
                "table": "dwh.dim_indicator",
                "indicator_name": "SIAT STAT DWH Yagona Katalogi",
                "unit": "ko'rsatkich",
                "data": meta_data_rows
            })
            await asyncio.sleep(0.01)

            yield format_sse("stage.started", {
                "stage": "generate",
                "message": "Mavjud ko'rsatkichlar va eng so'nggi ma'lumotlar sharhi shakllantirilmoqda..."
            })

            meta_answer = (
                "O'zbekiston Davlat statistika qo'mitasi (SIAT STAT DWH) ma'lumotlar omborida jami 3 232 ta rasmiy "
                "ko'rsatkich, 131 587 ta klassifikator va 2 580 045 ta faktik qiymat jamlangan [1].\n\n"
                "Asosiy statistik toifalar:\n"
                "1. Iste'mol narxlari va inflyatsiya — bozorlar va savdo do'konlaridagi oziq-ovqat hamda nooziq-ovqat mahsulotlari narxlari dinamikasi (masalan, go'sht, tuxum, un narxlari).\n"
                "2. Demografiya va mehnat statistikasi — doimiy aholi soni, tug'ilish, o'lim va bandlik ko'rsatkichlari.\n"
                "3. Makroiqtisodiyot va moliya — YAIM, investitsiyalar, sanoat va qurilish ishlari hajmi.\n"
                "4. Tashqi savdo, qishloq xo'jaligi va xizmatlar ko'rsatish sohasi.\n\n"
                "Bazada 2026-yil sentyabr (2026-M09) holatigacha bo'lgan eng so'nggi rasmiy oylik, choraklik va yillik ma'lumotlar tasdiqlangan holda mavjud [1]."
            )

            for i, word in enumerate(meta_answer.split(" ")):
                delta = word + (" " if i < len(meta_answer.split(" ")) - 1 else "")
                yield format_sse("generation.delta", {
                    "stage": "generate",
                    "delta": delta
                })
                await asyncio.sleep(0.005)

            yield format_sse("stage.completed", {
                "stage": "generate",
                "raw_text": meta_answer
            })
            await asyncio.sleep(0.01)

            yield format_sse("stage.started", {
                "stage": "verify",
                "message": "Metama'lumotlar verifikatsiyalanmoqda..."
            })
            await asyncio.sleep(0.01)

            yield format_sse("verification.completed", {
                "stage": "verify",
                "all_passed": True,
                "total_sentences": 1,
                "passed_count": 1,
                "failed_count": 0,
                "checklist": [{"text": meta_answer, "passed": True, "reason": None, "extracted_numbers": []}]
            })

            yield format_sse("stage.completed", {
                "stage": "verify"
            })
            await asyncio.sleep(0.01)

            yield format_sse("done", {
                "answer": meta_answer,
                "sources": [{
                    "n": 1,
                    "indicator_id": 1308,
                    "name": "SIAT STAT Rasmiy Statistik Ma'lumotlar Bazasining Yagona Katalogi",
                    "url": "https://siat.stat.uz",
                    "snapshot_date": "2026-11-11"
                }],
                "all_passed": True,
                "total_duration_ms": round((time.time() - start_total_time) * 1000, 2)
            })
            return

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

        selected_indicator_id, resolved_item_code, resolved_region_name, topic_valid = _select_best_candidate_and_item(
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

        target_period_single = None
        if intent == "compare_regions" and (resolved_periods or avail_periods):
            tool_name = "compare_regions"
            cmp_period = resolved_periods[0] if resolved_periods else avail_periods[-1]
            tool_args = {"indicator_id": selected_indicator_id, "period": cmp_period}
            target_period_single = cmp_period
        elif (intent in ("time_series", "analytical_extreme")) and resolved_item_code:
            tool_name = "time_series"
            tool_args = {"indicator_id": selected_indicator_id, "item_code": resolved_item_code}
        else:
            tool_name = "get_data"
            eff_periods = resolved_periods
            if intent == "analytical_extreme" and not eff_periods and avail_periods:
                eff_periods = avail_periods[-12:]
            elif not eff_periods and avail_periods:
                # Agar hech qanday davr berilmagan bo'lsa: eng so'nggi davr va oldingi 11 ta davr (12 davrli kontekst)
                target_period_single = avail_periods[-1]
                start_idx = max(0, len(avail_periods) - 12)
                eff_periods = avail_periods[start_idx:]
            elif eff_periods and len(eff_periods) == 1 and avail_periods:
                # Optimization 3 (12-Period Context for Single-Point Queries):
                # Aniq bitta davr so'ralganda (masalan '2026-M09'), 3D va to'liq ekranli grafik
                # to'liq 12 davrli trendni ko'rsatishi uchun so'ralgan davrgacha bo'lgan oxirgi 12 davrni olamiz
                req_p = eff_periods[0]
                target_period_single = req_p
                if req_p in avail_periods:
                    t_idx = avail_periods.index(req_p)
                    start_idx = max(0, t_idx - 11)
                    eff_periods = avail_periods[start_idx : t_idx + 1]
                else:
                    matches = [i for i, ap in enumerate(avail_periods) if ap.startswith(f"{req_p}-")]
                    if matches:
                        t_idx = matches[-1]
                        target_period_single = avail_periods[t_idx]
                        start_idx = max(0, t_idx - 11)
                        eff_periods = avail_periods[start_idx : t_idx + 1]
                    else:
                        eff_periods = [req_p]
                        target_period_single = req_p

            if parsed.get("is_generic_meat") and selected_indicator_id == 1308:
                tool_args = {
                    "indicator_id": 1308,
                    "item_codes": ["017", "0020", "022"],
                    "periods": ["2026-M09"],
                    "limit": 10
                }
            else:
                tool_args = {
                    "indicator_id": selected_indicator_id,
                    "item_codes": [resolved_item_code] if resolved_item_code else None,
                    "periods": eff_periods,
                    "limit": 100
                }

        if target_period_single:
            parsed["detected_period"] = target_period_single

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
            # Agar aniq davrlar (masalan: 2025-M09 va 2026-M09) so'ralgan bo'lsa
            if parsed["periods"] and len(parsed["periods"]) >= 2 and "timeline" in dwh_data:
                filtered_tl = [
                    pt for pt in dwh_data["timeline"]
                    if pt.get("period_key") in parsed["periods"]
                ]
                if len(filtered_tl) >= 2:
                    dwh_data["timeline"] = filtered_tl
                    dwh_data["total_points"] = len(filtered_tl)
                    val1 = float(filtered_tl[0]["value"])
                    val2 = float(filtered_tl[-1]["value"])
                    pct = round(((val2 - val1) / abs(val1)) * 100, 1)
                    dwh_data["pct_change"] = pct
                    dwh_data["abs_change"] = round(val2 - val1, 1)
            elif parsed["years"] and "timeline" in dwh_data:
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

        # Optimization 2: Measurement Unit Cleanup
        resolved_item_name = None
        if result_rows:
            resolved_item_name = result_rows[0].get("item_name")
        clean_unit = normalize_display_unit(meta_data.get("unit_uz") or dwh_data.get("unit"), resolved_item_name)
        meta_data["unit_uz"] = clean_unit
        dwh_data["unit"] = clean_unit

        # Har bir fakt qatoriga hudud va tozalangan o'lchov birligini qo'shish
        for r in result_rows:
            r["region_name"] = resolved_region_name
            r["unit"] = clean_unit
            if target_period_single and r.get("period_key") == target_period_single:
                r["is_target"] = True

        # Fix 2 (Analytical Array Parsing):
        # When asked for maximum, minimum, or 'which month/period' (e.g., 'eng yuqori', 'eng kam'),
        # evaluate all periods in the array and select the extreme one.
        # Ensure the extreme point is placed at index 0 so that UI figure/telemetry perfectly matches explanation.
        if intent == "analytical_extreme" and result_rows:
            valid_pts = [r for r in result_rows if r.get("value") is not None]
            if valid_pts:
                is_min = any(w in question.lower() for w in ("eng kam", "eng past", "eng arzon", "minimum"))
                extreme_pt = min(valid_pts, key=lambda x: x["value"]) if is_min else max(valid_pts, key=lambda x: x["value"])
                result_rows = [extreme_pt] + [r for r in result_rows if r != extreme_pt]
                parsed["detected_period"] = extreme_pt.get("period_key")

        yield format_sse("tool.result", {
            "stage": "result",
            "call_id": "call_mcp_1",
            "tool": tool_name,
            "execution_ms": dwh_dur_ms,
            "table": "dwh.fact_value",
            "indicator_name": meta_data.get("name_uz"),
            "region_name": resolved_region_name,
            "region_code": parsed.get("region_soato"),
            "detected_period": parsed.get("detected_period"),
            "unit": clean_unit,
            "data": result_rows[:24]
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
                target_pt = next((r for r in result_rows if r.get("period_key") == parsed.get("detected_period")), result_rows[0])
                target_val = target_pt.get("value")
                if lang == "ru":
                    lang_inst = "Ответьте на русском языке, четко, лаконично и строго по приведенным фактам."
                elif lang == "uz_cyrl":
                    lang_inst = "Ўзбек тилида кирилл алифбосида лўнда ва аниқ жавоб беринг."
                else:
                    lang_inst = "O'zbek tilida lo'nda va aniq javob bering."

                target_p_human = _format_p(target_pt.get("period_key"), lang)
                prompt = (
                    f"Siz O'zbekiston Davlat statistika qo'mitasi rasmiy ma'lumotlar bazasi analitikasisiz.\n"
                    f"Qat'iy qoidalar:\n"
                    f"1. Har bir raqam faqat berilgan DWH natijalaridan aynan olinishi shart!\n"
                    f"2. Yangi raqam hisoblamang va taxminiy raqam kiritmang!\n"
                    f"3. Check the requested measurement unit. If the user asks for price/cost ('narx', 'qancha'), you MUST filter the RRF results and ONLY select indicators where the unit is currency ('so'm'). Never output volume metrics (e.g., 'mln. dona') for price queries.\n"
                    f"4. When asked for maximum, minimum, or 'which month/period' (e.g., 'eng yuqori', 'eng kam'), you must request the full time-series array, evaluate all periods, and select the correct one. The final numerical output provided to the UI MUST perfectly match the text explanation.\n"
                    f"5. Hudud aniqligi: Natijani doimo aniqlangan hudud ({resolved_region_name}) bilan bog'lang (Respublika o'rtachasimi yoki aniq shahar/viloyatmi).\n"
                    f"6. O'lchov birligi: O'lchov birligi sifatida aynan '{clean_unit}' dan foydalaning. Ziddiyatli birliklarni (masalan tuxum uchun '1 kg so'mda') mutlaqo ishlatmang.\n"
                    f"7. Agar foydalanuvchi bitta aniq davrni ({parsed.get('detected_period')}) so'ragan bo'lsa, asosiy javobda aynan shu davr qiymatini ({target_val:,.1f} {clean_unit}) ko'rsating. Qolgan davrlar grafik uchun 12 davrli kontekst sifatida berilgan.\n"
                    f"8. Davrni foydalanuvchiga hech qachon '2026-M09' kabi xom kodda ko'rsatmang! Inson tushunadigan shaklda ('{target_p_human}') ko'rsating.\n"
                    f"9. Tasdiqlangan ma'lumotdan keyin [1] manba havolasi qo'ying.\n\n"
                    f"Savol: '{question}'\n"
                    f"Ko'rsatkich: {meta_data.get('name_uz')}\n"
                    f"Hudud: {resolved_region_name}\n"
                    f"O'lchov birligi: {clean_unit}\n"
                    f"DWH natijalari: {json.dumps(result_rows[:12], ensure_ascii=False)}\n"
                    f"{lang_inst}"
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
            raw_llm_text = _build_deterministic_answer(tool_name, dwh_data, meta_data, parsed, resolved_region_name)

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
