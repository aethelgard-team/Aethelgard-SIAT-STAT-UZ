# SSE Protokoli va Ma'lumotlar Shartnomasi (Frontend <-> Backend)

Holat: Tasdiqlangan va to'liq verifikatsiyalangan.
Maydonlar agent/orchestrator.py, agent/normalizer.py hamda frontend/src/ui/askView.js bilan 100% mos.

- Backend: FastAPI, http://localhost:8000 (CORS ochiq)
- Frontend: Vite Three.js 3D interfeysi, http://localhost:5173 (/api va /health 8000-portga proxy qilinadi)

## 1. REST Endpointlar

| Endpoint | Nima qaytaradi |
|---|---|
| POST /api/ask body: {"question": "..."} | SSE oqimi (text/event-stream), 7 bosqichli voqealar ketma-ketligi |
| GET /api/indicators/search?q=&lang=&limit= | {query, count, results: [{indicator_id, code, name_uz, unit, periodicity, rrf_score, matched_sources}]} |
| GET /api/indicators/{id} | metadata (name_uz, unit_uz, periodicity, source_url, ...) + total_items_count, sample_items |
| GET /api/series?indicator_id=&item_codes=&from=&to=&limit= | {total_returned, data: [{item_code, item_name, period_key, value, status, snapshot_date, source_url}]} |
| GET /api/stats | {total_indicators, total_items, total_periods, total_facts, valid_facts, zero_marked_facts, categories} |
| GET /health | {status: "ok" \| "degraded", database_connected: true} |

## 2. Server-Sent Events (SSE) Voqealari Ketma-ketligi

Standart va murakkab (compound) so'rovlarda quyidagi voqealar chiqariladi:

| Voqea Nomi | data Maydonlari Tavsifi |
|---|---|
| stage.started (parse) | {stage: "parse", message: "Savol tahlil qilinmoqda va normallashtirilmoqda..."} |
| stage.completed (parse) | {stage: "parse", lang: "uz_latn" \| "uz_cyrl" \| "ru", normalized_query, detected_period, detected_periods, detected_item_code, detected_region, region_code, intent, sub_queries: [...]} |
| stage.started (search) | {stage: "search", message: "DWH katalogidan RRF gibrid qidiruv amalga oshirilmoqda..."} |
| search.completed | {stage: "search", query, execution_ms, selected_indicator_id, topic_valid, total_matches, results: [{indicator_id, name_uz, unit, periodicity, rrf_score}]} |
| stage.completed (search) | {stage: "search", selected_indicator_id} |
| tool.called | {stage: "tool", call_id, tool, arguments} |
| stage.started (dwh) | {stage: "dwh", table: "dwh.fact_value", message: "DWH bazasidan ... ma'lumotlari o'qilmoqda..."} |
| stage.completed (dwh) | {stage: "dwh", table: "dwh.fact_value", execution_ms, rows_count} |
| tool.result | {stage: "result", call_id, tool, execution_ms, table, indicator_name, region_name, detected_period, unit, data: [...], sub_results: [...]} |
| stage.started (generate) | {stage: "generate", message: "Javob shakllantirilmoqda..."} |
| generation.delta | {stage: "generate", delta: "..."} |
| stage.completed (generate) | {stage: "generate", raw_text} |
| stage.started (verify) | {stage: "verify", message: "Nol-gallyutsinatsiya tekshiruvi..."} |
| verification.completed | {stage: "verify", all_passed, total_sentences, passed_count, failed_count, checklist: [{text, passed, reason, extracted_numbers}]} |
| stage.completed (verify) | {stage: "verify"} |
| done | {answer, sources: [{n, indicator_id, name, url, snapshot_date}], all_passed: true, sub_results: [...], total_duration_ms} |
| error | {message} |

## 3. Murakkab (Compound) So'rovlar Uchun sub_results Sxemasi

So'rov bir nechta mustaqil ko'rsatkichlarni o'z ichiga olganda (masalan: "mol go'shti narxi, tuxum narxi va Toshkent aholisi nechta?"), `tool.result` va `done` voqealarida `sub_results` ro'yxati uzatiladi:

```json
[
  {
    "index": 1,
    "title": "Mol go'shti",
    "indicator_id": 1308,
    "indicator_name": "Bozorlar va do'konlardagi ayrim tovarlarning o'rtacha narxlari dinamikasi",
    "region": "O'zbekiston Respublikasi",
    "period_raw": "2026-M09",
    "period_label": "2026-yil sentyabr oyi",
    "value": 127857.3,
    "unit": "so'm (1 kg)",
    "series": [
      {
        "period_key": "2025-M10",
        "value": 111624.1,
        "period_label": "2025-yil oktyabr oyi",
        "item_name": "Mol go'shti"
      }
    ]
  }
]
```

## 4. Inson Tushunadigan Davr Formatlari (Human-Readable Periods)

Raw DWH kodlari avtomatik ravishda foydalanuvchi tiliga moslashtiriladi:
- YYYY-M01 .. YYYY-M12 -> uz_latn: "YYYY-yil oy oyi", uz_cyrl: "YYYY йил ой ойи", ru: "месяц YYYY года"
- YYYY-Y00 / YYYY -> uz_latn: "YYYY-yil", uz_cyrl: "YYYY йил", ru: "YYYY год"
- YYYY-Q01 .. YYYY-Q04 -> uz_latn: "YYYY-yil N-chorak", uz_cyrl: "YYYY йил N-чорак", ru: "N-й квартал YYYY года"
