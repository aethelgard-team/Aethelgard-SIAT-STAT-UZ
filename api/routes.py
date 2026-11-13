"""
=============================================================================
SIAT STAT DWH: FastAPI Routes (api/routes.py)
Loyiha: siat.stat.uz MCP Loyihasi
Muallif: Siddiq (Backend & Database Lead)
Tavsif:
  FastAPI endpointlari:
  - POST /api/ask (SSE voqealar oqimi)
  - GET  /api/indicators/search (RRF gibrid qidiruvi)
  - GET  /api/indicators/{id} (Metama'lumotlar)
  - GET  /api/series (Vaqt qatorlari faktlari)
  - GET  /api/stats (Baza umumiy statistikasi)
  - GET  /health (Salomatlik tekshiruvi)
=============================================================================
"""

from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from mcp_server import tools
from mcp_server.db import get_db_cursor
from agent.orchestrator import orchestrate_question

router = APIRouter()


class AskRequest(BaseModel):
    question: str = Field(..., description="Foydalanuvchi bergan statistik savol", example="2026-yil sentyabrda mol go'shtining o'rtacha narxi qancha edi?")


# -----------------------------------------------------------------------------
# 1. POST /api/ask (SSE Stream)
# -----------------------------------------------------------------------------
@router.post("/api/ask", summary="Savolga 7 bosqichli SSE oqimida javob berish")
async def ask_question_stream(req: AskRequest):
    """
    Foydalanuvchi savolini qabul qilib, tahlil, qidiruv, MCP vositalari, DWH o'qish,
    generatsiya va nol-gallyutsinatsiya verifikatsiyasini o'z ichiga olgan
    7 bosqichli Server-Sent Events (SSE) oqimini qaytaradi.
    """
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Savol matni bo'sh bo'lishi mumkin emas.")

    return StreamingResponse(
        orchestrate_question(req.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# -----------------------------------------------------------------------------
# 2. GET /api/indicators/search
# -----------------------------------------------------------------------------
@router.get("/api/indicators/search", summary="RRF Gibrid Qidiruvi")
def search_indicators(
    q: str = Query(..., description="Qidiruv matni"),
    lang: str = Query("uz", description="Til (uz, ru, en)"),
    limit: int = Query(10, ge=1, le=50, description="Natijalar soni")
):
    """Ko'rsatkichlar va klassifikatorlar bo'yicha RRF gibrid qidiruvi."""
    return tools.search_indicators(query=q, limit=limit)


# -----------------------------------------------------------------------------
# 3. GET /api/indicators/{id}
# -----------------------------------------------------------------------------
@router.get("/api/indicators/{indicator_id}", summary="Ko'rsatkich metama'lumotlari")
def get_indicator(indicator_id: int):
    """Ko'rsatkichning 4 tildagi nomlari, birligi va metama'lumotlarini qaytaradi."""
    meta = tools.get_indicator_metadata(indicator_id)
    if "error" in meta:
        raise HTTPException(status_code=404, detail=meta["error"])
    return meta


# -----------------------------------------------------------------------------
# 4. GET /api/series
# -----------------------------------------------------------------------------
@router.get("/api/series", summary="Vaqt qatorlari faktlari")
def get_series(
    indicator_id: int = Query(..., description="Ko'rsatkich ID si"),
    item_codes: Optional[str] = Query(None, description="Vergul bilan ajratilgan kodlar (masalan: 017,001)"),
    from_period: Optional[str] = Query(None, alias="from", description="Boshlang'ich davr"),
    to_period: Optional[str] = Query(None, alias="to", description="Tugash davri"),
    limit: int = Query(500, ge=1, le=1000, description="Maksimal qatorlar soni")
):
    """Muayyan ko'rsatkich bo'yicha vaqt qatorlari faktlarini filtrlab oladi."""
    codes_list = [c.strip() for c in item_codes.split(",")] if item_codes else None

    # Agar from yoki to berilgan bo'lsa
    periods_filter = None
    if from_period or to_period:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT period_key 
                FROM dwh.dim_period 
                WHERE (%s IS NULL OR period_key >= %s)
                  AND (%s IS NULL OR period_key <= %s)
                ORDER BY period_key ASC;
            """, (from_period, from_period, to_period, to_period))
            periods_filter = [r["period_key"] for r in cur.fetchall()]

    return tools.get_data(
        indicator_id=indicator_id,
        item_codes=codes_list,
        periods=periods_filter,
        limit=limit
    )


# -----------------------------------------------------------------------------
# 5. GET /api/stats
# -----------------------------------------------------------------------------
@router.get("/api/stats", summary="DWH bazasi umumiy statistikasi")
def get_stats():
    """DWH omboridagi jami ko'rsatkichlar, klassifikatorlar va faktlar soni."""
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT 
                (SELECT count(*) FROM dwh.dim_indicator) AS total_indicators,
                (SELECT count(*) FROM dwh.dim_item) AS total_items,
                (SELECT count(*) FROM dwh.dim_period) AS total_periods,
                (SELECT count(*) FROM dwh.fact_value) AS total_facts,
                (SELECT count(*) FROM dwh.fact_value WHERE status = 'valid') AS valid_facts,
                (SELECT count(*) FROM dwh.fact_value WHERE status = 'zero_marked') AS zero_marked_facts,
                (SELECT count(DISTINCT snapshot_date) FROM dwh.fact_value) AS snapshot_dates_count;
        """)
        row = cur.fetchone()

        cur.execute("""
            SELECT split_part(code, '.', 1) AS section,
                   count(*)                 AS count,
                   array_agg(indicator_id ORDER BY indicator_id) AS indicator_ids
            FROM dwh.dim_indicator
            WHERE code IS NOT NULL
            GROUP BY 1
            ORDER BY 1;
        """)
        cat_rows = cur.fetchall()

    categories = [
        {
            "section": r["section"],
            "count": r["count"],
            "indicator_ids": r["indicator_ids"]
        }
        for r in cat_rows
    ]

    return {
        "status": "online",
        "database": "siat_dwh",
        "total_indicators": row["total_indicators"],
        "total_items": row["total_items"],
        "total_periods": row["total_periods"],
        "total_facts": row["total_facts"],
        "valid_facts": row["valid_facts"],
        "zero_marked_facts": row["zero_marked_facts"],
        "snapshot_date": "2026-11-11",
        "categories": categories
    }


# -----------------------------------------------------------------------------
# 6. GET /health
# -----------------------------------------------------------------------------
@router.get("/health", summary="Tizim salomatligi tekshiruvi")
def health_check():
    """Tizim va baza aloqasini tekshiruvchi salomatlik endpointi."""
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT 1;")
        return {
            "status": "ok",
            "service": "siat-stat-uz-api",
            "version": "1.0.0",
            "database_connected": True
        }
    except Exception as e:
        return {
            "status": "degraded",
            "service": "siat-stat-uz-api",
            "version": "1.0.0",
            "database_connected": False,
            "error": str(e)
        }
