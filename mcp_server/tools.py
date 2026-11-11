"""
=============================================================================
SIAT STAT DWH: AI Agent MCP Tools Module (mcp_server/tools.py)
Loyiha: siat.stat.uz MCP Server
Muallif: Siddiq (Backend & Database Lead)
Tavsif:
  AI Agentlar (Claude, Cursor, Gemini) uchun 6 ta asosiy DWH vositalari:
  1. search_indicators: Gibrid RRF qidiruvi orqali ko'rsatkichlarni topish
  2. get_indicator_metadata: Ko'rsatkichning to'liq metama'lumotlari
  3. get_data: Faktik statistik qiymatlar (zero_marked ajratilgan)
  4. compare_regions: Hududlar bo'yicha ko'rsatkichlarni solishtirish
  5. time_series: Vaqt dinamikasi va o'sish sur'atlari
  6. get_available_periods: Mavjud yillar va oylar ro'yxati
=============================================================================
"""

import math
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from mcp_server.db import get_db_cursor
from mcp_server.search import rrf_hybrid_search


# -----------------------------------------------------------------------------
# 1. Pydantic Modellar (Validatsiya va Tipizatsiya)
# -----------------------------------------------------------------------------
class IndicatorSummary(BaseModel):
    indicator_id: int = Field(description="SIAT ko'rsatkich identifikatori")
    code: Optional[str] = Field(None, description="Rasmiy klassifikatsiya kodi")
    name_uz: str = Field(description="O'zbekcha nomi")
    name_ru: Optional[str] = Field(None, description="Ruscha nomi")
    name_en: Optional[str] = Field(None, description="Inglizcha nomi")
    unit: Optional[str] = Field(None, description="O'lchov birligi")
    periodicity: Optional[str] = Field(None, description="Davriyligi (oylik, yillik, choraklik)")
    score: float = Field(description="RRF qidiruv moslik reytingi")
    matched_items: List[str] = Field(default_factory=list, description="Mos kelgan ichki mahsulotlar/klassifikatorlar")


class FactRecord(BaseModel):
    indicator_id: int
    indicator_name: str
    item_code: str
    item_name: str
    period_key: str
    value: Optional[float]
    raw_value: Optional[str]
    status: str
    is_zero_marked: bool
    snapshot_date: str
    source_url: str


# -----------------------------------------------------------------------------
# 2. Tool Funksiyalari
# -----------------------------------------------------------------------------
def search_indicators(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    RRF (Reciprocal Rank Fusion) gibrid qidiruv orqali SIAT ko'rsatkichlarini topadi.

    Ushbu vosita to'liq matnli (Full-Text) va noaniq (Trigram) qidiruvni birlashtirib,
    ham ko'rsatkich nomlari, ham ichki tovar/mahsulot nomlari bo'yicha eng mos
    datasetlarni qaytaradi.

    Args:
        query: Qidiruv iborasi (masalan: "mol go'shti narxi", "aholi soni", "inflyatsiya").
        limit: Qaytariladigan ko'rsatkichlar soni (standart: 10, maksimum: 30).

    Returns:
        Mos kelgan ko'rsatkichlar ro'yxati, ularning ID si, o'lchov birligi va RRF bali.
    """
    safe_limit = max(1, min(limit, 30))
    hits = rrf_hybrid_search(query, limit=safe_limit)
    return {
        "query": query,
        "count": len(hits),
        "results": hits
    }


def get_indicator_metadata(indicator_id: int) -> Dict[str, Any]:
    """
    Statistik ko'rsatkichning to'liq metama'lumotlari va tarkibini qaytaradi.

    Ko'rsatkichning 4 tildagi nomlari, o'lchov birligi, metodikasi, mas'ul boshqarma,
    oxirgi rasmiy yangilangan sana va klassifikator namunalari haqida axborot beradi.

    Args:
        indicator_id: Ko'rsatkichning unikal SIAT ID si (masalan: 1308).

    Returns:
        Ko'rsatkich metama'lumotlari lug'ati.
    """
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT 
                indicator_id, code,
                name_uz, name_ru, name_en, name_uzc,
                unit_uz, unit_ru, unit_en, unit_uzc,
                periodicity, organization, methodology, notes,
                last_modified_date, source_url, is_cumulative,
                created_at, updated_at
            FROM dwh.dim_indicator
            WHERE indicator_id = %s;
        """, (indicator_id,))
        indicator = cur.fetchone()

        if not indicator:
            return {
                "error": f"Ko'rsatkich #{indicator_id} DWH bazasida topilmadi.",
                "indicator_id": indicator_id
            }

        # Klassifikator qatorlari soni va dastlabki namunalari
        cur.execute("""
            SELECT count(*) AS total_items 
            FROM dwh.dim_item 
            WHERE indicator_id = %s;
        """, (indicator_id,))
        total_items = cur.fetchone()["total_items"]

        cur.execute("""
            SELECT item_code, name_uz 
            FROM dwh.dim_item 
            WHERE indicator_id = %s 
            ORDER BY item_code ASC 
            LIMIT 5;
        """, (indicator_id,))
        sample_items = [dict(r) for r in cur.fetchall()]

        res = dict(indicator)
        res["total_items_count"] = total_items
        res["sample_items"] = sample_items
        # Sanalarni satrga aylantirish
        if res.get("last_modified_date"):
            res["last_modified_date"] = str(res["last_modified_date"])
        if res.get("created_at"):
            res["created_at"] = str(res["created_at"])
        if res.get("updated_at"):
            res["updated_at"] = str(res["updated_at"])
        return res


def get_data(
    indicator_id: int,
    item_codes: Optional[List[str]] = None,
    periods: Optional[List[str]] = None,
    limit: int = 500
) -> Dict[str, Any]:
    """
    Muayyan ko'rsatkich bo'yicha faktik ma'lumotlarni filtrlab oladi.

    DIQQAT: Agar status = 'zero_marked' bo'lsa, bu qiymat aslida 0.0 bo'lib,
    ma'lumot kiritilmagani yoki mavsumiylikni bildiradi (tahliliy qiymati NULL).
    Faqat status = 'valid' bo'lgan qiymatlar rasmiy hisoblashga yaroqlidir.

    Args:
        indicator_id: Ko'rsatkich ID si (masalan: 1308).
        item_codes: Klassifikator kodlari ro'yxati (masalan: ["017"] - Mol go'shti).
        periods: Olinishi kerak bo'lgan davrlar ro'yxati (masalan: ["2026-M09", "2025-M09"]).
        limit: Qaytariladigan maksimal qatorlar soni (standart: 500).

    Returns:
        Faktik qatorlar ro'yxati va metama'lumotlar.
    """
    safe_limit = max(1, min(limit, 1000))
    query_parts = ["""
        SELECT 
            f.indicator_id,
            i.name_uz AS indicator_name,
            it.item_code,
            it.name_uz AS item_name,
            f.period_key,
            p.year,
            p.quarter,
            p.month,
            p.period_type,
            f.value,
            f.raw_value,
            f.status,
            f.snapshot_date,
            i.source_url
        FROM dwh.fact_value f
        JOIN dwh.dim_indicator i ON f.indicator_id = i.indicator_id
        JOIN dwh.dim_item it ON f.item_id = it.item_id
        LEFT JOIN dwh.dim_period p ON f.period_key = p.period_key
        WHERE f.indicator_id = %s
    """]
    params: List[Any] = [indicator_id]

    if item_codes:
        str_item_codes = [str(c).strip() for c in item_codes]
        query_parts.append("AND it.item_code = ANY(%s)")
        params.append(str_item_codes)

    if periods:
        norm_periods = [str(p).replace("М", "M").replace("м", "M").strip() for p in periods]
        query_parts.append("AND f.period_key = ANY(%s)")
        params.append(norm_periods)

    query_parts.append("ORDER BY it.item_code ASC, f.period_key ASC LIMIT %s;")
    params.append(safe_limit)

    full_sql = "\n".join(query_parts)

    with get_db_cursor() as cur:
        cur.execute(full_sql, params)
        rows = cur.fetchall()

    records = []
    zero_marked_count = 0
    valid_count = 0

    for r in rows:
        d = dict(r)
        d["value"] = float(d["value"]) if d["value"] is not None else None
        d["is_zero_marked"] = (d["status"] == "zero_marked")
        d["snapshot_date"] = str(d["snapshot_date"]) if d.get("snapshot_date") else None
        if d["is_zero_marked"]:
            zero_marked_count += 1
        elif d["status"] == "valid":
            valid_count += 1
        records.append(d)

    return {
        "indicator_id": indicator_id,
        "total_returned": len(records),
        "valid_count": valid_count,
        "zero_marked_count": zero_marked_count,
        "data": records
    }


def compare_regions(indicator_id: int, period: str) -> Dict[str, Any]:
    """
    Berilgan davr uchun O'zbekiston hududlari (viloyatlar va shaharlar) ko'rsatkichlarini
    qiymat bo'yicha kamayish tartibida saralab solishtiradi.

    Args:
        indicator_id: Hududiy taqsimotga ega ko'rsatkich ID si (masalan: 273).
        period: Davr kaliti (masalan: "2024", "2026-M09", "2024-Q3").

    Returns:
        Tartiblangan reyting (O'zbekiston Respublikasi umumiy ko'rsatkichi alohida ajratiladi).
    """
    norm_period = period.replace("М", "M").replace("м", "M").strip()

    with get_db_cursor() as cur:
        cur.execute("""
            SELECT 
                it.item_code,
                it.name_uz AS region_name,
                f.value,
                f.raw_value,
                f.status,
                i.name_uz AS indicator_name,
                i.unit_uz AS unit
            FROM dwh.fact_value f
            JOIN dwh.dim_item it ON f.item_id = it.item_id
            JOIN dwh.dim_indicator i ON f.indicator_id = i.indicator_id
            WHERE f.indicator_id = %s AND f.period_key = %s
              AND (
                  it.name_uz ILIKE '%%viloyat%%' 
                  OR it.name_uz ILIKE '%%Respublikasi%%' 
                  OR it.name_uz ILIKE '%%shahri%%'
              )
            ORDER BY f.value DESC NULLS LAST;
        """, (indicator_id, norm_period))
        rows = cur.fetchall()

    if not rows:
        # Agar maxsus hududiy nomlar topilmasa, barcha klassifikatorlarni solishtiramiz
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT 
                    it.item_code,
                    it.name_uz AS region_name,
                    f.value,
                    f.raw_value,
                    f.status,
                    i.name_uz AS indicator_name,
                    i.unit_uz AS unit
                FROM dwh.fact_value f
                JOIN dwh.dim_item it ON f.item_id = it.item_id
                JOIN dwh.dim_indicator i ON f.indicator_id = i.indicator_id
                WHERE f.indicator_id = %s AND f.period_key = %s
                ORDER BY f.value DESC NULLS LAST;
            """, (indicator_id, norm_period))
            rows = cur.fetchall()

    ranking = []
    republic_total = None

    rank = 1
    for r in rows:
        val = float(r["value"]) if r["value"] is not None else None
        item_dict = {
            "item_code": r["item_code"],
            "region_name": r["region_name"],
            "value": val,
            "raw_value": r["raw_value"],
            "status": r["status"]
        }

        # Umumrespublika ko'rsatkichini alohida ajratib qo'yish
        if "o'zbekiston respublikasi" in r["region_name"].lower() or r["item_code"] == "1700":
            republic_total = item_dict
        else:
            item_dict["rank"] = rank
            ranking.append(item_dict)
            rank += 1

    return {
        "indicator_id": indicator_id,
        "indicator_name": rows[0]["indicator_name"] if rows else None,
        "period": norm_period,
        "unit": rows[0]["unit"] if rows else None,
        "republic_benchmark": republic_total,
        "ranking_count": len(ranking),
        "ranking": ranking
    }


def time_series(indicator_id: int, item_code: str) -> Dict[str, Any]:
    """
    Muayyan mahsulot yoki hududning butun davrlar bo'yicha dinamikasini va
    davrdan-davrga o'zgarish foizini xronologik tartibda hisoblab chiqaradi.

    Args:
        indicator_id: Ko'rsatkich ID si (masalan: 1308).
        item_code: Qator kodi (masalan: "017" - Mol go'shti).

    Returns:
        Xronologik vaqt qatori, davriy o'zgarish (farq) va foiz ko'rsatkichlari.
    """
    str_code = str(item_code).strip()

    with get_db_cursor() as cur:
        cur.execute("""
            SELECT 
                i.name_uz AS indicator_name,
                i.unit_uz AS unit,
                it.item_code,
                it.name_uz AS item_name,
                f.period_key,
                p.year,
                p.month,
                p.quarter,
                p.period_type,
                f.value,
                f.raw_value,
                f.status
            FROM dwh.fact_value f
            JOIN dwh.dim_indicator i ON f.indicator_id = i.indicator_id
            JOIN dwh.dim_item it ON f.item_id = it.item_id
            LEFT JOIN dwh.dim_period p ON f.period_key = p.period_key
            WHERE f.indicator_id = %s AND it.item_code = %s
            ORDER BY 
                p.year ASC NULLS LAST, 
                COALESCE(p.month, p.quarter, 0) ASC, 
                f.period_key ASC;
        """, (indicator_id, str_code))
        rows = cur.fetchall()

    if not rows:
        return {
            "error": f"Ko'rsatkich #{indicator_id} va item_code='{item_code}' bo'yicha ma'lumot topilmadi.",
            "indicator_id": indicator_id,
            "item_code": item_code
        }

    points = []
    prev_val = None

    for r in rows:
        val = float(r["value"]) if r["value"] is not None else None

        abs_diff = None
        pct_growth = None

        if val is not None and prev_val is not None and prev_val != 0:
            abs_diff = round(val - prev_val, 4)
            pct_growth = round(((val - prev_val) / prev_val) * 100, 2)

        point = {
            "period_key": r["period_key"],
            "year": r["year"],
            "value": val,
            "raw_value": r["raw_value"],
            "status": r["status"],
            "abs_change": abs_diff,
            "pct_change": pct_growth
        }
        points.append(point)

        if val is not None:
            prev_val = val

    return {
        "indicator_id": indicator_id,
        "indicator_name": rows[0]["indicator_name"],
        "item_code": str_code,
        "item_name": rows[0]["item_name"],
        "unit": rows[0]["unit"],
        "total_points": len(points),
        "timeline": points
    }


def get_available_periods(indicator_id: int) -> Dict[str, Any]:
    """
    Ushbu ko'rsatkich bo'yicha bazada qaysi yillar, oylar yoki davrlar
    mavjudligini ko'rsatadi.

    Args:
        indicator_id: Ko'rsatkich ID si (masalan: 1308).

    Returns:
        Mavjud davrlar ro'yxati, minimal va maksimal davr hamda yillar to'plami.
    """
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT DISTINCT 
                f.period_key,
                p.year,
                p.month,
                p.quarter,
                p.period_type
            FROM dwh.fact_value f
            LEFT JOIN dwh.dim_period p ON f.period_key = p.period_key
            WHERE f.indicator_id = %s
            ORDER BY p.year ASC NULLS LAST, f.period_key ASC;
        """, (indicator_id,))
        rows = cur.fetchall()

    if not rows:
        return {
            "error": f"Ko'rsatkich #{indicator_id} bo'yicha davrlar topilmadi.",
            "indicator_id": indicator_id
        }

    periods = [r["period_key"] for r in rows]
    years = sorted(list({r["year"] for r in rows if r["year"] is not None}))
    period_types = sorted(list({r["period_type"] for r in rows if r.get("period_type")}))

    return {
        "indicator_id": indicator_id,
        "total_periods": len(periods),
        "min_period": periods[0],
        "max_period": periods[-1],
        "years": years,
        "period_types": period_types,
        "periods": periods
    }
