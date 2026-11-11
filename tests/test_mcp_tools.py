"""
=============================================================================
SIAT STAT DWH: MCP Tools Test Suite (tests/test_mcp_tools.py)
Loyiha: siat.stat.uz MCP Server
Muallif: Siddiq (Backend & Database Lead)
Tavsif:
  Barcha 6 ta MCP asboblarini real DWH bazasida avtomatlashtirilgan tekshiruvi:
  1. search_indicators
  2. get_indicator_metadata
  3. get_data (1308-dataset "Mol go'shti, 2026-M09" benchmark verifikatsiyasi)
  4. compare_regions
  5. time_series
  6. get_available_periods
=============================================================================
"""

import sys
import time
import os

# Loyiha ildizini import yo'liga qo'shish
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_server import tools


def run_all_tests():
    print("=" * 75)
    print("SIAT STAT DWH: MCP TOOLS TEST VA VERIFIKATSIYA SUITE")
    print("=" * 75)

    passed_tests = 0
    total_tests = 6

    # -------------------------------------------------------------------------
    # TEST 1: search_indicators (RRF Hybrid Search)
    # -------------------------------------------------------------------------
    print("\n[TEST 1/6] search_indicators: RRF Gibrid Qidiruv...")
    t0 = time.time()
    res1 = tools.search_indicators("mol go'shti", limit=5)
    t1 = time.time()
    dur1 = (t1 - t0) * 1000

    print(f"  * Qidiruv vaqti: {dur1:.2f} ms")
    print(f"  * Topilgan natijalar soni: {res1['count']} ta")

    # Tekshiruv: 1308 topildimi?
    found_1308 = any(r["indicator_id"] == 1308 for r in res1["results"])
    top_hit = res1["results"][0] if res1["results"] else None
    if top_hit:
        print(f"  * 1-o'rindagi natija: #{top_hit['indicator_id']} - {top_hit['name_uz']} (Score: {top_hit['rrf_score']})")

    assert res1["count"] > 0, "Hech qanday natija topilmadi!"
    assert found_1308, "1308-ko'rsatkich qidiruv natijalarida chiqmadi!"
    print("  -> [OK] search_indicators testi muvaffaqiyatli o'tdi.")
    passed_tests += 1

    # -------------------------------------------------------------------------
    # TEST 2: get_indicator_metadata
    # -------------------------------------------------------------------------
    print("\n[TEST 2/6] get_indicator_metadata: Ko'rsatkich metama'lumotlari...")
    t0 = time.time()
    res2 = tools.get_indicator_metadata(indicator_id=1308)
    dur2 = (time.time() - t0) * 1000

    print(f"  * Ijro vaqti: {dur2:.2f} ms")
    print(f"  * Nomi (UZ): {res2.get('name_uz')}")
    print(f"  * Kodi: {res2.get('code')}")
    print(f"  * Birligi: {res2.get('unit_uz')}")
    print(f"  * Jami klassifikatorlar soni: {res2.get('total_items_count')}")

    assert "error" not in res2, f"Xatolik: {res2.get('error')}"
    assert res2.get("total_items_count", 0) > 0, "Klassifikatorlar topilmadi!"
    print("  -> [OK] get_indicator_metadata testi muvaffaqiyatli o'tdi.")
    passed_tests += 1

    # -------------------------------------------------------------------------
    # TEST 3: get_data (Benchmark: Mol go'shti, 2026-M09)
    # -------------------------------------------------------------------------
    print("\n[TEST 3/6] get_data: Faktik qiymatlar va 1308 Benchmark Tekshiruvi...")
    t0 = time.time()
    res3 = tools.get_data(
        indicator_id=1308,
        item_codes=["017"],
        periods=["2026-M09"]
    )
    dur3 = (time.time() - t0) * 1000

    print(f"  * Ijro vaqti: {dur3:.2f} ms")
    print(f"  * Qaytarilgan qatorlar: {res3['total_returned']}")

    assert res3["total_returned"] == 1, f"Kutilgan 1 qator o'rniga {res3['total_returned']} ta keldi!"
    fact = res3["data"][0]
    val = fact["value"]
    expected_val = 127857.3

    print(f"  * Mahsulot: {fact['item_name']} (Kod: {fact['item_code']})")
    print(f"  * Davr: {fact['period_key']}")
    print(f"  * Qiymat: {val:,.1f} so'm (status: {fact['status']}, zero_marked: {fact['is_zero_marked']})")

    assert abs(val - expected_val) < 0.01, f"Qiymat mos kelmadi: {val} != {expected_val}"
    assert fact["status"] == "valid", "Status valid emas!"
    assert not fact["is_zero_marked"], "Mol go'shti narxi noto'g'ri zero_marked deb belgilangan!"
    print(f"  -> [OK] get_data benchmark testi muvaffaqiyatli o'tdi ({val} == {expected_val}).")
    passed_tests += 1

    # -------------------------------------------------------------------------
    # TEST 4: compare_regions
    # -------------------------------------------------------------------------
    print("\n[TEST 4/6] compare_regions: Hududlar reytingi (Ind #273, 2024)...")
    t0 = time.time()
    res4 = tools.compare_regions(indicator_id=273, period="2024")
    dur4 = (time.time() - t0) * 1000

    print(f"  * Ijro vaqti: {dur4:.2f} ms")
    print(f"  * Reytingdagi hududlar: {res4['ranking_count']} ta")
    if res4.get("republic_benchmark"):
        print(f"  * Respublika ko'rsatkichi (Benchmark): {res4['republic_benchmark']['value']}")

    assert res4["ranking_count"] > 0, "Hududlar reytingi bo'sh!"
    top_region = res4["ranking"][0]
    print(f"  * 1-o'rindagi hudud: {top_region['region_name']} (Qiymat: {top_region['value']})")

    # Kamayish tartibida saralanganligini tekshirish
    values = [r["value"] for r in res4["ranking"] if r["value"] is not None]
    assert values == sorted(values, reverse=True), "Hududlar qiymat bo'yicha kamayish tartibida emas!"
    print("  -> [OK] compare_regions testi muvaffaqiyatli o'tdi.")
    passed_tests += 1

    # -------------------------------------------------------------------------
    # TEST 5: time_series
    # -------------------------------------------------------------------------
    print("\n[TEST 5/6] time_series: Vaqt dinamikasi va o'sish sur'atlari (Ind #1308, '017')...")
    t0 = time.time()
    res5 = tools.time_series(indicator_id=1308, item_code="017")
    dur5 = (time.time() - t0) * 1000

    print(f"  * Ijro vaqti: {dur5:.2f} ms")
    print(f"  * Jami vaqt nuqtalari: {res5.get('total_points')} ta")

    assert res5.get("total_points", 0) > 10, "Vaqt qatori nuqtalari kam!"
    first_pt = res5["timeline"][0]
    last_pt = res5["timeline"][-1]
    print(f"  * Dastlabki davr: {first_pt['period_key']} -> {first_pt['value']} so'm")
    print(f"  * Oxirgi davr: {last_pt['period_key']} -> {last_pt['value']} so'm (O'sish: {last_pt['pct_change']}%)")

    assert last_pt["period_key"] == "2026-M09", "Oxirgi davr 2026-M09 emas!"
    assert last_pt["pct_change"] is not None, "O'zgarish foizi hisoblanmagan!"
    print("  -> [OK] time_series testi muvaffaqiyatli o'tdi.")
    passed_tests += 1

    # -------------------------------------------------------------------------
    # TEST 6: get_available_periods
    # -------------------------------------------------------------------------
    print("\n[TEST 6/6] get_available_periods: Mavjud davrlar tahlili...")
    t0 = time.time()
    res6 = tools.get_available_periods(indicator_id=1308)
    dur6 = (time.time() - t0) * 1000

    print(f"  * Ijro vaqti: {dur6:.2f} ms")
    print(f"  * Jami davrlar: {res6.get('total_periods')} ta")
    print(f"  * Davr oralig'i: {res6.get('min_period')} dan {res6.get('max_period')} gacha")
    print(f"  * Yillar: {res6.get('years')}")

    assert res6.get("total_periods", 0) > 0, "Davrlar topilmadi!"
    assert "2026-M09" in res6.get("periods", []), "2026-M09 davri ro'yxatda yo'q!"
    print("  -> [OK] get_available_periods testi muvaffaqiyatli o'tdi.")
    passed_tests += 1

    # -------------------------------------------------------------------------
    # XULOSA
    # -------------------------------------------------------------------------
    print("\n" + "=" * 75)
    print(f"TEST NATIJALARI: {passed_tests}/{total_tests} ta test to'liq muvaffaqiyatli o'tdi! (100%)")
    print("=" * 75)


if __name__ == "__main__":
    run_all_tests()
