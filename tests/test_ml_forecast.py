"""
Aethelgard SIAT: ML Time-Series Forecasting Test Suite (tests/test_ml_forecast.py)
Author: Siddiq (Backend & ML Lead)

Tests:
1. Mathematical forecaster (Ridge Regression, Holt-Winters ETS, ARIMA)
2. Backtest model selection and 95% confidence intervals
3. Insufficient data (< 3 points) and extreme horizon (> 2036) guards
4. FastMCP tool `forecast_indicator` execution against DWH
5. Multi-script & multi-language intent detection (Uzbek Latin, Cyrillic, Russian)
6. Zero-Hallucination verifier validation
7. End-to-end SSE orchestrator stream (single and compound queries)
"""

import sys
import os
import asyncio
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ml.forecaster import run_time_series_forecast
from mcp_server import tools
from agent.normalizer import detect_forecast_intent, is_out_of_scope_query, normalize_input_query
from agent.verifier import verify_text
from agent.orchestrator import analyze_question_full, orchestrate_question


def test_1_forecaster_annual():
    print("[TEST 1/8] ML Forecaster: Yillik ma'lumotlar bo'yicha prognoz...")
    # 2015-2025 yillik o'suvchi trend
    hist = [{"period_key": str(y), "year": y, "value": 30.0 + (y - 2015) * 1.5} for y in range(2015, 2026)]
    res = run_time_series_forecast(hist, target_year=2030, indicator_name="Doimiy aholi", unit="mln kishi")

    assert res["status"] == "success", f"Kutilmagan status: {res}"
    assert res["target_year"] == 2030
    assert res["predicted_value"] > 44.0, f"Prognoz juda past: {res['predicted_value']}"
    assert res["lower_bound"] <= res["predicted_value"] <= res["upper_bound"]
    assert res["confidence_level"] == 95
    assert res["model_used"] in ("Ridge Regression", "Holt-Winters ETS", "ARIMA(1, 1, 0)", "ARIMA(0, 1, 1)", "ARIMA(1, 0, 0)")
    assert len(res["forecast_series"]) == 5  # 2026, 2027, 2028, 2029, 2030
    print(f"  -> [OK] Model: {res['model_used']}, Prognoz: {res['predicted_value']} (95% CI: [{res['lower_bound']} - {res['upper_bound']}]), MAPE: {res['mape']}%")


def test_2_forecaster_monthly():
    print("[TEST 2/8] ML Forecaster: Oylik vaqt qatori bo'yicha prognoz...")
    # 36 oylik ma'lumot (2023-M01 dan 2025-M12 gacha)
    hist = []
    val = 10000.0
    for y in (2023, 2024, 2025):
        for m in range(1, 13):
            val += 150.0
            hist.append({"period_key": f"{y}-M{m:02d}", "year": y, "month": m, "value": val})

    res = run_time_series_forecast(hist, target_year=2028, indicator_name="Mol go'shti narxi", unit="so'm")
    assert res["status"] == "success"
    assert res["target_year"] == 2028
    assert res["predicted_value"] > val
    assert res["lower_bound"] <= res["predicted_value"] <= res["upper_bound"]
    assert len(res["forecast_series"]) > 0
    print(f"  -> [OK] Oylik prognoz muvaffaqiyatli: {res['predicted_value']} so'm, Model: {res['model_used']}")


def test_3_forecaster_guards():
    print("[TEST 3/8] ML Forecaster: Kam ma'lumot (<3) va Ekstremal Gorizont (>2036) tekshiruvi...")
    # < 3 points
    few = [{"period_key": "2024", "value": 100.0}, {"period_key": "2025", "value": 110.0}]
    r_few = run_time_series_forecast(few, 2028)
    assert r_few["status"] == "error"
    assert r_few["error_code"] == "INSUFFICIENT_DATA"

    # > 2036
    valid = [{"period_key": str(y), "year": y, "value": 50.0 + y} for y in range(2020, 2026)]
    r_ext = run_time_series_forecast(valid, 2045)
    assert r_ext["status"] == "error"
    assert r_ext["error_code"] == "EXTREME_HORIZON"
    print("  -> [OK] Barcha himoya to'siqlari to'g'ri ishladi.")


def test_4_fastmcp_forecast_indicator():
    print("[TEST 4/8] FastMCP: forecast_indicator tool'ini DWH bazasida chaqirish...")
    # Ind #1308 (Go'sht narxlari dinamikasi) bo'yicha 2028-yil prognozi
    res = tools.forecast_indicator(indicator_id=1308, target_year=2028, item_code="017")
    assert res.get("status") == "success", f"DWH forecast xatosi: {res}"
    assert res["indicator_id"] == 1308
    assert res["target_year"] == 2028
    assert res["predicted_value"] > 0
    assert res["confidence_level"] == 95
    assert res["lower_bound"] <= res["predicted_value"] <= res["upper_bound"]
    print(f"  -> [OK] DWH #1308 prognozi: {res['predicted_value']} {res['unit']} (Model: {res['model_used']}, MAPE: {res['mape']}%)")


def test_5_multilingual_intent_detection():
    print("[TEST 5/8] Normalizer: Ko'p tilli prognoz niyatini aniqlash...")
    q1 = "2030-yilda go'sht narxi qancha bo'ladi?"
    i1 = analyze_question_full(q1)
    assert i1["intent"] == "forecast"
    assert i1["target_year"] == 2030
    assert not i1["is_unsupported"]

    q2 = "2028 йилда аҳоли сони кутилмоқда?"
    i2 = analyze_question_full(q2)
    assert i2["intent"] == "forecast"
    assert i2["target_year"] == 2028

    q3 = "Прогноз уровня инфляции на 2029 год"
    i3 = analyze_question_full(q3)
    assert i3["intent"] == "forecast"
    assert i3["target_year"] == 2029

    # Yil aytilmagan, lekin prognoz kalit so'zi bor
    q4 = "Kelajakda go'sht narxi qanday bo'ladi?"
    i4 = analyze_question_full(q4)
    assert i4["intent"] == "forecast"
    assert i4["target_year"] == 2027

    # Ekstremal yil (> 2036)
    q5 = "2045-yilda aholi soni qancha bo'ladi?"
    i5 = analyze_question_full(q5)
    assert i5["intent"] == "unsupported"
    assert i5["unsupported_reason"] == "extreme_forecast"

    # Out of scope
    q6 = "Bitcoin narxi 2030-yilda qancha bo'ladi?"
    i6 = analyze_question_full(q6)
    assert i6["intent"] == "unsupported"
    assert i6["unsupported_reason"] == "out_of_scope"

    print("  -> [OK] 3 tildagi barcha prognoz va tuzoq so'rovlari 100% aniq yo'naltirildi.")


def test_6_zero_hallucination_verifier():
    print("[TEST 6/8] Zero-Hallucination: Prognoz raqamlari verifikatsiyasi...")
    fc_data = {
        "status": "success",
        "indicator_name": "Mol go'shti narxi",
        "item_name": "Mol go'shti",
        "target_year": 2029,
        "predicted_value": 142500.0,
        "lower_bound": 128000.0,
        "upper_bound": 157000.0,
        "confidence_level": 95,
        "model_used": "ARIMA(1, 1, 0)",
        "mape": 2.14,
        "history_count": 69,
        "history_range": "2021-M01 - 2026-M09"
    }

    # Haqiqiy javob
    valid_text = (
        "2029-yil uchun Mol go'shti bo'yicha matematik ML prognoz (ARIMA(1, 1, 0) modeli asosida) "
        "142,500.0 so'mni tashkil etadi (95% ishonch oralig'i: 128,000.0 — 157,000.0 so'm, MAPE: 2.14%). "
        "Ushbu ko'rsatkich rasmiy statistika emas, balki 2021-M01 - 2026-M09 yillardagi 69 ta "
        "retrospektiv DWH faktlariga asoslangan matematik ekstrapolyatsiyadir [1]."
    )
    v_ok = verify_text(valid_text, fc_data)
    assert v_ok["all_passed"], f"Haqiqiy matn verifikatsiyadan o'tmadi: {v_ok}"

    # Gallyutsinatsiya qilingan raqam qo'shilgan matn (masalan 999999 so'm)
    hallucinated_text = (
        "2029-yil uchun Mol go'shti bo'yicha prognoz 999,999.0 so'mni tashkil etadi [1]."
    )
    v_fail = verify_text(hallucinated_text, fc_data)
    assert not v_fail["all_passed"], "Gallyutsinatsiya qilingan raqam to'xtatilmadi!"
    print("  -> [OK] Zero-Hallucination verifikatori prognoz raqamlarini to'liq tasdiqladi va soxtasini to'xtatdi.")


async def _collect_sse_events(query: str) -> List[Dict[str, Any]]:
    events = []
    import json
    async for sse in orchestrate_question(query):
        chunks = sse.strip().split("\n\n")
        for chunk in chunks:
            if not chunk.strip():
                continue
            lines = chunk.strip().split("\n")
            ev_name = ""
            ev_data = {}
            for l in lines:
                if l.startswith("event:"):
                    ev_name = l.replace("event:", "", 1).strip()
                elif l.startswith("data:"):
                    data_str = l.replace("data:", "", 1).strip()
                    try:
                        ev_data = json.loads(data_str)
                    except Exception:
                        ev_data = {}
            if ev_name:
                events.append({"event": ev_name, "data": ev_data})
    return events


def test_7_orchestrator_forecast_stream():
    print("[TEST 7/8] Orchestrator: Yakka prognoz so'rovi SSE oqimi (2030 mol go'shti)...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        events = loop.run_until_complete(_collect_sse_events("2030-yilda mol go'shti narxi qancha bo'ladi?"))
    finally:
        loop.close()

    ev_names = [e["event"] for e in events]
    assert "stage.started" in ev_names
    assert "search.completed" in ev_names
    assert "tool.called" in ev_names

    tool_call_ev = next(e for e in events if e["event"] == "tool.called")
    assert tool_call_ev["data"].get("tool") == "forecast_indicator"

    tool_res_ev = next(e for e in events if e["event"] == "tool.result")
    assert tool_res_ev["data"].get("is_forecast") is True
    assert tool_res_ev["data"].get("predicted_value") is not None

    chart_data = tool_res_ev["data"].get("data", [])
    assert len(chart_data) > 0 and len(chart_data) <= 24, f"Chart series downsampling failed, length: {len(chart_data)}"
    last_point = chart_data[-1]
    assert last_point.get("period_key") == "2030" or last_point.get("year") == 2030, f"Last chart point is not 2030: {last_point}"
    assert last_point.get("is_forecast") is True, "Last chart point is not marked as forecast"

    done_ev = next(e for e in events if e["event"] == "done")
    assert done_ev["data"].get("all_passed") is True
    ans = done_ev["data"].get("answer", "")
    assert "prognoz" in ans.lower() or "прогноз" in ans.lower()

    primary_kpi = done_ev["data"].get("primary_kpi")
    assert primary_kpi is not None, "primary_kpi is missing in done event"
    assert primary_kpi.get("is_forecast") is True, "primary_kpi.is_forecast must be True"
    assert primary_kpi.get("value") is not None and primary_kpi["value"] > 140000, f"Hero KPI value {primary_kpi.get('value')} is wrong (must be ~173,433, not 69,973)"
    assert primary_kpi.get("last_actual_value") is not None, "last_actual_value missing in primary_kpi"
    assert primary_kpi.get("last_actual_period") is not None, "last_actual_period missing in primary_kpi"
    print(f"  -> [OK] Hero KPI: {primary_kpi['value']:,.1f} {primary_kpi.get('unit')} (last actual: {primary_kpi['last_actual_value']:,.1f} at {primary_kpi['last_actual_period']}).")
    print(f"  -> [OK] Chart timeline length: {len(chart_data)} points (ending at {last_point.get('period_key')}).")
    print(f"  -> [OK] SSE oqimi to'liq o'tdi. Yakuniy javob: {ans[:90]}...")


def test_8_compound_mixed_forecast():
    print("[TEST 8/8] Orchestrator: Murakkab aralash so'rov (tarixiy + prognoz)...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        events = loop.run_until_complete(_collect_sse_events("mol go'shti narxi va 2030-yilda go'sht narxi qancha bo'ladi?"))
    finally:
        loop.close()

    done_ev = next(e for e in events if e["event"] == "done")
    assert done_ev["data"].get("all_passed") is True
    assert done_ev["data"].get("sub_results") is not None
    assert len(done_ev["data"]["sub_results"]) >= 2
    ans = done_ev["data"].get("answer", "")
    assert "1." in ans and "2." in ans
    print(f"  -> [OK] Murakkab aralash so'rov (tarixiy + 2030 prognoz) 100% muvaffaqiyatli yakunlandi.")


def run_all():
    print("=" * 75)
    print("AETHELGARD SIAT: MACHINE LEARNING FORECASTING TEST SUITE")
    print("=" * 75)
    test_1_forecaster_annual()
    test_2_forecaster_monthly()
    test_3_forecaster_guards()
    test_4_fastmcp_forecast_indicator()
    test_5_multilingual_intent_detection()
    test_6_zero_hallucination_verifier()
    test_7_orchestrator_forecast_stream()
    test_8_compound_mixed_forecast()
    print("=" * 75)
    print("NATIJA: Barcha 8/8 ta ML prognozlash testlari 100% muvaffaqiyatli o'tdi!")
    print("=" * 75)


if __name__ == "__main__":
    run_all()
