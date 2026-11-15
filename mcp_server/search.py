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
    "ish haqi": "o'rtacha oylik nominal hisoblangan ish haqi",
    "maosh": "ish haqi",
    "yhm": "yalpi hududiy mahsulot",
    "yaim": "yalpi ichki mahsulot",
    "eksport": "tovarlar eksporti",
    "import": "tovarlar importi",
    "inflyatsiya": "iste'mol narxlari indeksi"
}


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

    # Sinonim tekshiruvi: qisqartma va so'zlashuv atamalarini almashtirish
    expanded_query = raw_norm
    token_synonyms = {
        "yaim": "yalpi ichki mahsulot",
        "yhm": "yalpi hududiy mahsulot",
        "inflyatsiya": "iste'mol narxlari indeksi",
        "maosh": "ish haqi",
    }
    for term, syn in token_synonyms.items():
        if re.search(rf"\b{re.escape(term)}\b", expanded_query):
            expanded_query = re.sub(rf"\b{re.escape(term)}\b", syn, expanded_query)

    if raw_norm in SYNONYMS and raw_norm == expanded_query:
        expanded_query = SYNONYMS[raw_norm]

    ts_query_str = build_tsquery_string(expanded_query)
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
        try:
            cur.execute("""
                SELECT 
                    it.indicator_id, i.code, i.name_uz, i.name_ru, i.name_en,
                    i.unit_uz, i.periodicity, it.name_uz AS item_name,
                    similarity(dwh.normalize_text(it.name_uz), dwh.normalize_text(%s)) AS item_sim
                FROM dwh.dim_item it
                JOIN dwh.dim_indicator i ON it.indicator_id = i.indicator_id
                WHERE similarity(dwh.normalize_text(it.name_uz), dwh.normalize_text(%s)) > 0.25
                ORDER BY item_sim DESC, it.indicator_id ASC
                LIMIT 30;
            """, (raw_norm, raw_norm))
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
