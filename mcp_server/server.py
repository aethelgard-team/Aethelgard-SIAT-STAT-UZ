"""
=============================================================================
SIAT STAT DWH: Model Context Protocol (MCP) Server (mcp_server/server.py)
Loyiha: siat.stat.uz MCP Server
Muallif: Siddiq (Backend & Database Lead)
Tavsif:
  Claude Desktop va MCP Inspector orqali 2.58M qatorli DWH
  ma'lumotlarini taqdim etuvchi rasmiy MCP server.
  Transport: stdio (standart) yoki sse / streamable-http.
=============================================================================
"""

import sys
import argparse
from typing import List, Dict, Any, Optional

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer

from mcp_server import tools

# -----------------------------------------------------------------------------
# 1. MCP Serverni yaratish
# -----------------------------------------------------------------------------
mcp = MCPServer(
    name="siat-stat-uz"
)


# -----------------------------------------------------------------------------
# 2. Vositlarni (Tools) ro'yxatdan o'tkazish
# -----------------------------------------------------------------------------
@mcp.tool()
def search_indicators(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    RRF (Reciprocal Rank Fusion) gibrid qidiruvi orqali SIAT ko'rsatkichlarini topadi.

    Ushbu vosita to'liq matnli (Full-Text) va noaniq (Trigram) qidiruvni birlashtirib,
    ko'rsatkich nomlari hamda ichki tovar/mahsulot nomlari bo'yicha mos datasetlarni qaytaradi.

    Args:
        query: Qidiruv iborasi (masalan: "mol go'shti narxi", "aholi soni", "inflyatsiya").
        limit: Qaytariladigan ko'rsatkichlar soni (standart: 10).
    """
    return tools.search_indicators(query=query, limit=limit)


@mcp.tool()
def get_indicator_metadata(indicator_id: int) -> Dict[str, Any]:
    """
    Statistik ko'rsatkichning to'liq metama'lumotlari va tarkibini qaytaradi.

    Ko'rsatkichning 4 tildagi nomlari, o'lchov birligi, metodikasi, mas'ul boshqarma,
    oxirgi rasmiy yangilangan sana va klassifikator namunalari haqida axborot beradi.

    Args:
        indicator_id: Ko'rsatkichning unikal SIAT ID si (masalan: 1308).
    """
    return tools.get_indicator_metadata(indicator_id=indicator_id)


@mcp.tool()
def get_data(
    indicator_id: int,
    item_codes: Optional[List[str]] = None,
    periods: Optional[List[str]] = None,
    limit: int = 500
) -> Dict[str, Any]:
    """
    Muayyan ko'rsatkich bo'yicha faktik statistik qiymatlarni filtrlab oladi.

    DIQQAT: Agar status = 'zero_marked' bo'lsa, bu qiymat aslida 0.0 bo'lib,
    ma'lumot kiritilmagani yoki mavsumiylikni bildiradi (tahliliy qiymati NULL).
    Faqat status = 'valid' bo'lgan qiymatlar rasmiy hisoblashga yaroqlidir.

    Args:
        indicator_id: Ko'rsatkich ID si (masalan: 1308).
        item_codes: Klassifikator kodlari ro'yxati (masalan: ["017"] - Mol go'shti).
        periods: Olinishi kerak bo'lgan davrlar ro'yxati (masalan: ["2026-M09", "2025-M09"]).
        limit: Qaytariladigan maksimal qatorlar soni (standart: 500).
    """
    return tools.get_data(
        indicator_id=indicator_id,
        item_codes=item_codes,
        periods=periods,
        limit=limit
    )


@mcp.tool()
def compare_regions(indicator_id: int, period: str) -> Dict[str, Any]:
    """
    Berilgan davr uchun O'zbekiston hududlari (viloyatlar va shaharlar) ko'rsatkichlarini
    qiymat bo'yicha kamayish tartibida saralab solishtiradi.

    Args:
        indicator_id: Hududiy taqsimotga ega ko'rsatkich ID si (masalan: 273).
        period: Davr kaliti (masalan: "2024", "2026-M09", "2024-Q3").
    """
    return tools.compare_regions(indicator_id=indicator_id, period=period)


@mcp.tool()
def time_series(indicator_id: int, item_code: str) -> Dict[str, Any]:
    """
    Muayyan mahsulot yoki hududning butun davrlar bo'yicha dinamikasini va
    davrdan-davrga o'zgarish foizini xronologik tartibda hisoblab chiqaradi.

    Args:
        indicator_id: Ko'rsatkich ID si (masalan: 1308).
        item_code: Qator kodi (masalan: "017" - Mol go'shti).
    """
    return tools.time_series(indicator_id=indicator_id, item_code=item_code)


@mcp.tool()
def get_available_periods(indicator_id: int) -> Dict[str, Any]:
    """
    Ushbu ko'rsatkich bo'yicha bazada qaysi yillar, oylar yoki davrlar
    mavjudligini ko'rsatadi.

    Args:
        indicator_id: Ko'rsatkich ID si (masalan: 1308).
    """
    return tools.get_available_periods(indicator_id=indicator_id)


# -----------------------------------------------------------------------------
# 3. Serverni ishga tushirish
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="SIAT STAT DWH MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP aloqa protokoli (standart: stdio)"
    )
    args = parser.parse_args()

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
