"""
=============================================================================
SIAT STAT DWH: Smart Search Module (mcp_server/search.py)
Loyiha: siat.stat.uz MCP Server
Muallif: Siddiq (Backend & Database Lead)
Tavsif:
  Reciprocal Rank Fusion (RRF) gibrid qidiruvi:
  1. Full-Text Search (tsvector + ts_rank_cd)
  2. Trigram Fuzzy Search (pg_trgm) dim_indicator bo'yicha
  3. Trigram Fuzzy Search dim_item (klassifikatorlar) bo'yicha
  Natijalarni RRF formulasi: Score = SUM(1 / (60 + rank)) bilan birlashtirish.
=============================================================================
"""

import re
from typing import List, Dict, Any, Optional
from mcp_server.db import get_db_cursor

# Kichik so'zlashuv lug'ati (Tez-tez uchraydigan sinonimlar)
SYNONYMS = {
    "narx": "o'rtacha narxlar",
    "narxlar": "o'rtacha narxlar",
    "aholi": "doimiy aholi",
    "aholi soni": "doimiy aholi soni",
    "ish haqi": "o'rtacha hisoblangan oylik ish haqi",
    "maosh": "ish haqi",
    "yhm": "yalpi hududiy mahsulot",
    "yaim": "yalpi ichki mahsulot",
    "eksport": "tovarlar eksporti",
    "import": "tovarlar importi",
    "inflyatsiya": "iste'mol narxlari indeksi"
}

# Rasmiy SOATO hudud kodlari va nomlari
SOATO_REGIONS: Dict[str, str] = {
    "1700": "O'zbekiston Respublikasi",
    "1703": "Andijon viloyati",
    "1706": "Buxoro viloyati",
    "1708": "Jizzax viloyati",
    "1710": "Qashqadaryo viloyati",
    "1712": "Navoiy viloyati",
    "1714": "Namangan viloyati",
    "1718": "Samarqand viloyati",
    "1722": "Surxondaryo viloyati",
    "1724": "Sirdaryo viloyati",
    "1726": "Toshkent shahri",
    "1727": "Toshkent viloyati",
    "1730": "Farg'ona viloyati",
    "1733": "Xorazm viloyati",
    "1735": "Qoraqalpog'iston Respublikasi",
}

# O'zbekcha so'zlashuv iboralarini rasmiy statistik atamalarga kengaytirish
COLLOQUIAL_PATTERNS = [
    (r"\b(?:necha|nechi)\s+pul\b", "o'rtacha narxi"),
    (r"\bqancha\s+turadi\b", "o'rtacha narxi"),
    (r"\bodam\s+yashaydi\b", "doimiy aholi soni"),
    (r"\baholi\s+(?:nechta|qancha)\b", "doimiy aholi soni"),
    (r"\bqancha\s+aholi\b", "doimiy aholi soni"),
    (r"\b(?:oylik|maosh|ish\s*haqi)\b", "o'rtacha hisoblangan oylik ish haqi"),
    (r"\bpoytaxt(?:da|ga|ning)?\b", "Toshkent shahri"),
]

TOKEN_SYNONYMS = {
    "yaim": "yalpi ichki mahsulot",
    "yhm": "yalpi hududiy mahsulot",
    "inflyatsiya": "iste'mol narxlari indeksi",
}

REGION_PATTERNS = [
    (r"\btoshkent\s+viloyat(?:i|da|ga|ning)?\b", "1727"),
    (r"\btoshkent\s+shahar(?:i|da|ga|ning)?\b", "1726"),
    (r"\btoshkent\s+sh\.?\b", "1726"),
    (r"\bpoytaxt(?:da|ga|ning)?\b", "1726"),
    (r"\btoshkent(?:da|ga|ning)?\b", "1726"),
    (r"\bqoraqalpog['`]?iston\s+respublikasi\b", "1735"),
    (r"\bqoraqalpog['`]?iston(?:da|ga|ning)?\b", "1735"),
    (r"\bnukus(?:da|ga|ning)?\b", "1735"),
    (r"\bsamarqand\s+viloyat(?:i|da|ga|ning)?\b", "1718"),
    (r"\bsamarqand(?:da|ga|ning)?\b", "1718"),
    (r"\bandijon\s+viloyat(?:i|da|ga|ning)?\b", "1703"),
    (r"\bandijon(?:da|ga|ning)?\b", "1703"),
    (r"\bbuxoro\s+viloyat(?:i|da|ga|ning)?\b", "1706"),
    (r"\bbuxoro(?:da|ga|ning)?\b", "1706"),
    (r"\bfarg['`]?ona\s+viloyat(?:i|da|ga|ning)?\b", "1730"),
    (r"\bfarg['`]?ona(?:da|ga|ning)?\b", "1730"),
    (r"\bnamangan\s+viloyat(?:i|da|ga|ning)?\b", "1714"),
    (r"\bnamangan(?:da|ga|ning)?\b", "1714"),
    (r"\bqashqadaryo\s+viloyat(?:i|da|ga|ning)?\b", "1710"),
    (r"\bqashqadaryo(?:da|ga|ning)?\b", "1710"),
    (r"\bsurxondaryo\s+viloyat(?:i|da|ga|ning)?\b", "1722"),
    (r"\bsurxondaryo(?:da|ga|ning)?\b", "1722"),
    (r"\bnavoiy\s+viloyat(?:i|da|ga|ning)?\b", "1712"),
    (r"\bnavoiy(?:da|ga|ning)?\b", "1712"),
    (r"\bjizzax\s+viloyat(?:i|da|ga|ning)?\b", "1708"),
    (r"\bjizzax(?:da|ga|ning)?\b", "1708"),
    (r"\bsirdaryo\s+viloyat(?:i|da|ga|ning)?\b", "1724"),
    (r"\bsirdaryo(?:da|ga|ning)?\b", "1724"),
    (r"\bxorazm\s+viloyat(?:i|da|ga|ning)?\b", "1733"),
    (r"\bxorazm(?:da|ga|ning)?\b", "1733"),
    (r"\bo['`]?zbekiston\s+respublikasi\b", "1700"),
    (r"\bo['`]?zbekiston(?:da|ga|ning)?\b", "1700"),
    (r"\bress?publika(?:si)?(?:da|ga|ning)?\b", "1700"),
    (r"\bmamlakat(?:da|ga|ning)?\b", "1700"),
]


def resolve_region_from_text(text: str) -> Tuple[str, str, bool]:
    """
    Matndan rasmiy SOATO kodi va hudud nomini aniqlaydi.
    Returns:
        (soato_code, canonical_region_name, is_explicit)
    """
    t = re.sub(r"['`’‘ʻ]", "'", (text or "").lower().strip())
    for pat, code in REGION_PATTERNS:
        if re.search(pat, t):
            return code, SOATO_REGIONS[code], True
    return "1700", SOATO_REGIONS["1700"], False


def normalize_query(query: str) -> str:
    """Apostroflarni birxillashtirish va kichik harfga o'tkazish."""
    if not query:
        return ""
    q = query.strip()
    q = re.sub(r"['`’‘ʻ]", "'", q)
    return q.lower()


def _stem_uz(word: str) -> str:
    """Qidiruv uchun o'zbekcha asosiy qo'shimchalarni yengil qisqartirish."""
    if len(word) <= 4:
        return word
    for suf in ("lari", "ining", "ning", "dagi", "lar", "ini", "dan", "ni", "ga", "da", "si"):
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            return word[:-len(suf)]
    if word.endswith("i") and len(word) >= 5 and word not in ("yalpi", "ichki", "oylik", "yillik", "ishsizlik", "aholi"):
        return word[:-1]
    return word


def build_tsquery_string(normalized_query: str) -> Optional[str]:
    """To'liq matnli qidiruv uchun prefix tsquery ('word1:* & word2:*') yaratadi."""
    # Faqat harf va raqamlarni ajratib olish (lotin va kirill)
    words = re.findall(r"[a-zA-Z0-9\u0400-\u04FF]+", normalized_query)
    if not words:
        return None
    # Har bir so'zga stem + prefix qo'shish (kamida 2 ta harfli bo'lsa)
    terms = []
    for w in words:
        if len(w) >= 2:
            stemmed = _stem_uz(w)
            terms.append(f"{stemmed}:*")
    if not terms:
        terms = [f"{w}:*" for w in words]
    # Takroriy terminlarni olib tashlash
    seen = []
    for t in terms:
        if t not in seen:
            seen.append(t)
    return " & ".join(seen)


def rrf_hybrid_search(query: str, limit: int = 10, k: int = 60) -> List[Dict[str, Any]]:
    """
    RRF (Reciprocal Rank Fusion) asosidagi gibrid qidiruv.
    Formulasi: RRF_Score(d) = SUM( 1 / (k + rank_i(d)) )
    """
    raw_norm = normalize_query(query)
    if not raw_norm:
        return []

    # Sinonim tekshiruvi: qisqartma va so'zlashuv atamalarini kengaytirish
    expanded_query = raw_norm
    for pat, rep in COLLOQUIAL_PATTERNS:
        expanded_query = re.sub(pat, rep, expanded_query)
    for term, syn in TOKEN_SYNONYMS.items():
        if re.search(rf"\b{re.escape(term)}\b", expanded_query):
            expanded_query = re.sub(rf"\b{re.escape(term)}\b", syn, expanded_query)

    if raw_norm in SYNONYMS and raw_norm == expanded_query:
        expanded_query = SYNONYMS[raw_norm]

    # Hudud nomlarini FTS qidiruv shovqinidan ajratish
    fts_candidate_text = expanded_query
    for pat, _ in REGION_PATTERNS:
        fts_candidate_text = re.sub(pat, " ", fts_candidate_text)
    # Savol olmoshlari va shovqinlarni tozalash
    for sw in ("qancha", "necha", "nechta", "nechi", "qanday", "nima", "haqida", "edi", "bo'lgan", "bolgan"):
        fts_candidate_text = re.sub(rf"\b{re.escape(sw)}\b", " ", fts_candidate_text)

    ts_query_str = build_tsquery_string(fts_candidate_text.strip() or expanded_query)
    trgm_query = expanded_query if expanded_query != raw_norm else raw_norm

    scores: Dict[int, Dict[str, Any]] = {}

    with get_db_cursor() as cur:
        # ---------------------------------------------------------------------
        # 1. Full-Text Search (dim_indicator.search_vector)
        # ---------------------------------------------------------------------
        if ts_query_str:
            try:
                cur.execute("""
                    SELECT 
                        indicator_id, code, name_uz, name_ru, name_en,
                        unit_uz, periodicity,
                        ts_rank_cd(search_vector, to_tsquery('simple', %s)) AS fts_score
                    FROM dwh.dim_indicator
                    WHERE search_vector @@ to_tsquery('simple', %s)
                    ORDER BY fts_score DESC
                    LIMIT 30;
                """, (ts_query_str, ts_query_str))
                for rank, row in enumerate(cur.fetchall(), 1):
                    iid = row["indicator_id"]
                    if iid not in scores:
                        scores[iid] = {
                            "indicator_id": iid,
                            "code": row["code"],
                            "name_uz": row["name_uz"],
                            "name_ru": row["name_ru"],
                            "name_en": row["name_en"],
                            "unit": row["unit_uz"],
                            "periodicity": row["periodicity"],
                            "rrf_score": 0.0,
                            "matched_sources": [],
                            "matched_items": []
                        }
                    scores[iid]["rrf_score"] += 1.0 / (k + rank)
                    scores[iid]["matched_sources"].append(f"fts(rank={rank})")
            except Exception:
                pass  # So'rov noaniq bo'lsa xatoliksiz davom etadi

        # ---------------------------------------------------------------------
        # 2. Trigram Fuzzy Search (dim_indicator.name_uz)
        # ---------------------------------------------------------------------
        try:
            cur.execute("""
                SELECT 
                    indicator_id, code, name_uz, name_ru, name_en,
                    unit_uz, periodicity,
                    similarity(dwh.normalize_text(name_uz), dwh.normalize_text(%s)) AS trgm_score
                FROM dwh.dim_indicator
                WHERE similarity(dwh.normalize_text(name_uz), dwh.normalize_text(%s)) > 0.18
                ORDER BY trgm_score DESC, indicator_id ASC
                LIMIT 30;
            """, (trgm_query, trgm_query))
            for rank, row in enumerate(cur.fetchall(), 1):
                iid = row["indicator_id"]
                if iid not in scores:
                    scores[iid] = {
                        "indicator_id": iid,
                        "code": row["code"],
                        "name_uz": row["name_uz"],
                        "name_ru": row["name_ru"],
                        "name_en": row["name_en"],
                        "unit": row["unit_uz"],
                        "periodicity": row["periodicity"],
                        "rrf_score": 0.0,
                        "matched_sources": [],
                        "matched_items": []
                    }
                scores[iid]["rrf_score"] += 1.0 / (k + rank)
                scores[iid]["matched_sources"].append(f"trgm_indicator(rank={rank})")
        except Exception:
            pass

        # ---------------------------------------------------------------------
        # 3. Trigram Fuzzy Search (dim_item.name_uz - Mahsulot/hudud bo'yicha)
        # ---------------------------------------------------------------------
        item_query = raw_norm
        for pat, _ in REGION_PATTERNS:
            item_query = re.sub(pat, " ", item_query)
        for sw in ("narx", "narxi", "narxlari", "so'm", "som", "baho", "cena", "o'rtacha", "ortacha", "dinamika", "dinamikasi", "qancha", "necha", "nechta"):
            item_query = re.sub(rf"\b{re.escape(sw)}\b", " ", item_query)
        item_clean = " ".join(re.findall(r"[a-zA-Z0-9\u0400-\u04FF']+", item_query)).strip()
        search_item_target = item_clean if len(item_clean) >= 2 else raw_norm

        try:
            cur.execute("""
                SELECT 
                    it.indicator_id, i.code, i.name_uz, i.name_ru, i.name_en,
                    i.unit_uz, i.periodicity, it.name_uz AS item_name,
                    similarity(dwh.normalize_text(it.name_uz), dwh.normalize_text(%s)) AS item_sim
                FROM dwh.dim_item it
                JOIN dwh.dim_indicator i ON it.indicator_id = i.indicator_id
                WHERE similarity(dwh.normalize_text(it.name_uz), dwh.normalize_text(%s)) > 0.20
                ORDER BY item_sim DESC, it.indicator_id ASC
                LIMIT 50;
            """, (search_item_target, search_item_target))
            for rank, row in enumerate(cur.fetchall(), 1):
                iid = row["indicator_id"]
                if iid not in scores:
                    scores[iid] = {
                        "indicator_id": iid,
                        "code": row["code"],
                        "name_uz": row["name_uz"],
                        "name_ru": row["name_ru"],
                        "name_en": row["name_en"],
                        "unit": row["unit_uz"],
                        "periodicity": row["periodicity"],
                        "rrf_score": 0.0,
                        "matched_sources": [],
                        "matched_items": []
                    }
                scores[iid]["rrf_score"] += 1.0 / (k + rank)
                scores[iid]["matched_sources"].append(f"trgm_item(rank={rank})")
                if row["item_name"] not in scores[iid]["matched_items"]:
                    scores[iid]["matched_items"].append(row["item_name"])
        except Exception:
            pass

    # Agar foydalanuvchi jins yoki shahar/qishloq ko'rsatmagan bo'lsa, (jami) ga ustunlik berish
    prefer_total = not any(w in raw_norm for w in ("ayol", "erkak", "shahar", "qishloq"))
    if prefer_total:
        for item in scores.values():
            name_low = (item.get("name_uz") or "").lower()
            if "(jami)" in name_low:
                item["rrf_score"] += 0.0005

    # Fix 1 & 4 (Unit Semantic Matching & Consumer Food Price Boost):
    # Agar so'rov narx/qiymat haqida bo'lsa ('narx', 'narxi', 'so'm', 'baho', 'necha pul', 'qancha turadi'),
    # o'lchov birligi valyuta ('so'm', 'sum') bo'lgan ko'rsatkichlarga keskin ustunlik berish.
    # Non, go'sht, tuxum kabi tovarlar narx niyati bilan so'ralganda iste'mol narxlari ko'rsatkichlarini (#1308, #1327) kuchaytirish.
    has_food_item = any(w in raw_norm for w in ("non", "go'sht", "gosht", "tuxum", "un", "shakar", "kartoshka", "sabzi", "guruch", "yog'"))
    is_price_seeking = any(w in raw_norm or w in expanded_query for w in (
        "narx", "narxi", "narxlari", "so'm", "som", "baho", "цена", "стоимость", "price", "cost",
        "necha pul", "qancha turadi"
    )) or (has_food_item and any(w in raw_norm for w in ("qancha", "necha", "nechi")))

    if is_price_seeking:
        for item in scores.values():
            u_raw = item.get("unit") or ""
            u_norm = re.sub(r"['`’‘ʻ]", "'", u_raw.lower())
            name_low = (item.get("name_uz") or "").lower()
            if any(cu in u_norm for cu in ("so'm", "som", "сум", "sum")):
                item["rrf_score"] += 0.025
                if "o'rtacha narx" in name_low or "iste'mol narx" in name_low or "narxlari" in name_low:
                    item["rrf_score"] += 0.015
                if has_food_item and ("bozor" in name_low or "do'kon" in name_low):
                    item["rrf_score"] += 0.020
            elif any(vu in u_norm for vu in ("dona", "tonna", "metr", "litr", "birlik", "foiz", "kishi")) and not any(cu in u_norm for cu in ("so'm", "som", "сум", "sum")):
                item["rrf_score"] -= 0.025

    # Natijalarni RRF ballari kamayish tartibida saralash
    sorted_results = sorted(
        scores.values(),
        key=lambda x: (x["rrf_score"], -x["indicator_id"]),
        reverse=True
    )

    # Ballarni yaxlitlash
    for res in sorted_results:
        res["rrf_score"] = round(res["rrf_score"], 6)

    return sorted_results[:limit]
