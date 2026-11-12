# SSE shartnomasi (frontend ↔ backend)

> Holat: **kelishilgan** (Siddiq tasdiqladi). Maydonlar `agent/orchestrator.py` dagi
> haqiqiy voqealar bilan bir xil. O'zgartirish kerak bo'lsa — ikkalamiz kelishib.

- Backend: FastAPI, `http://localhost:8000` (CORS ochiq)
- Frontend: Vite, `http://localhost:5173` (`/api` va `/health` 8000-portga proxy qilinadi)

## Endpointlar

| Endpoint | Nima qaytaradi |
|---|---|
| `POST /api/ask` body: `{"question": "..."}` | SSE oqimi (`text/event-stream`), voqealar pastda |
| `GET /api/indicators/search?q=&lang=&limit=` | `{query, count, results: [{indicator_id, code, name_uz, unit, periodicity, rrf_score, matched_sources}]}` |
| `GET /api/indicators/{id}` | metadata (`name_uz`, `unit_uz`, `periodicity`, `source_url`, ...) + `total_items_count`, `sample_items` |
| `GET /api/series?indicator_id=&item_codes=&from=&to=&limit=` | `{total_returned, data: [{item_code, item_name, period_key, value, status, snapshot_date, source_url}]}` |
| `GET /api/stats` | `{total_indicators, total_items, total_periods, total_facts, valid_facts, zero_marked_facts}` |
| `GET /health` | `{status: "ok" \| "degraded", database_connected}` |

## SSE voqealari (ketma-ketlikda)

| Voqea | `data` |
|---|---|
| `stage.started` | `{stage, message}` — stage: `parse`, `search`, `dwh`, `generate`, `verify` |
| `stage.completed` (parse) | `{stage, lang, normalized_query, detected_period, detected_item_code}` |
| `search.completed` | `{stage, query, execution_ms, selected_indicator_id, total_matches, results}` |
| `stage.completed` (search) | `{stage, selected_indicator_id}` |
| `tool.called` | `{stage: "tool", call_id, tool, arguments}` — `tool` uchun alohida started/completed yo'q |
| `stage.completed` (dwh) | `{stage, table, execution_ms, rows_count}` |
| `tool.result` | `{stage: "result", call_id, tool, execution_ms, table, indicator_name, unit, data: [...]}` |
| `generation.delta` | `{stage: "generate", delta}` |
| `stage.completed` (generate) | `{stage, raw_text}` |
| `verification.completed` | `{stage, all_passed, total_sentences, passed_count, failed_count, checklist: [{text, passed, reason}]}` |
| `done` | `{answer, sources: [{n, indicator_id, name, url, snapshot_date}], all_passed, total_duration_ms}` |
| `error` | `{message}` |

Ko'rsatkich topilmasa: `search.completed` dan keyin darhol `done` keladi, `sources: []`.

## MCP tool'lar (`mcp_server/server.py`)
`search_indicators`, `get_indicator_metadata`, `get_data`, `compare_regions`, `time_series`, `get_available_periods`
