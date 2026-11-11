# Day 3: Model Context Protocol (MCP) Server va RRF Hybrid Search

## 1. Infratuzilma va Arxitektura

Tashqi AI agentlari (Claude Desktop, MCP Inspector) 2.58 million qatorli DWH ma'lumotlarini soniyaning ulushida qidirishi, filtrlay olishi va tahlil qilishi uchun standartlashtirilgan MCP server backend infratuzilmasi qurildi.

### Arxitektura komponentlari:
- `mcp_server/db.py`: `psycopg2.pool.ThreadedConnectionPool` (min: 2, max: 10) havzasi orqali xavfsiz va tezkor ma'lumotlar bazasi aloqasi. Natijalar `RealDictCursor` yordamida lug'at (`dict`) formatida olinadi.
- `mcp_server/search.py`: Reciprocal Rank Fusion (RRF) gibrid qidiruv moduli.
- `mcp_server/tools.py`: AI agentlar uchun 6 ta qat'iy tipizatsiyalangan analitik vosita.
- `mcp_server/server.py`: FastMCP / MCPServer kirish nuqtasi (`stdio`, `sse`, `streamable-http` protokollari qo'llab-quvvatlanadi).

Bazada tezkor so'rovlar uchun qo'shimcha indekslar:
```sql
CREATE INDEX IF NOT EXISTS idx_fact_indicator_period ON dwh.fact_value(indicator_id, period_key);
CREATE INDEX IF NOT EXISTS idx_fact_item_indicator ON dwh.fact_value(indicator_id, item_id);
```

---

## 2. RRF (Reciprocal Rank Fusion) Gibrid Qidiruv

Foydalanuvchilar qidiruv so'rovlarini noaniq yoki xatolar bilan kiritganda ham aniq natijani topish uchun uch qatlamli qidiruv va RRF reyting birlashtirish algoritmi tatbiq etildi:

### Algoritm bosqichlari:
1. **Full-Text Search (FTS):** `dwh.dim_indicator.search_vector @@ to_tsquery('simple', ...)` orqali `ts_rank_cd` reytingi bo'yicha saralash.
2. **Trigram Fuzzy Search (Ko'rsatkichlar):** `similarity(dwh.normalize_text(name_uz), %s) > 0.18` orqali ko'rsatkich sarlavhasidagi noaniqliklarni qidirish.
3. **Trigram Fuzzy Search (Klassifikatorlar):** `similarity(dwh.normalize_text(it.name_uz), %s) > 0.25` orqali ichki mahsulotlar (masalan, "Mol go'shti", "Benzin") bo'yicha to'g'ridan-to'g'ri tegishli datasetni topish.

### RRF Reyting Formulasi:
$$RRF\_Score(d) = \sum_{m \in M} \frac{1}{k + rank_m(d)}$$
Bu yerda:
- $M$: faol qidiruv manbalari to'plami (FTS, Trigram Indicator, Trigram Item)
- $k = 60$: standart tekislash doimiysi (smoothing constant)
- $rank_m(d)$: $m$-manbadagi 1-asosli tartib o'rni

---

## 3. Realizatsiya qilingan 6 ta MCP Vositalari (Tools)

| Vositachi (Tool) | Kirish parametrlari | Tavsifi va Qaytuvchi Ma'lumot |
|---|---|---|
| `search_indicators` | `query: str, limit: int = 10` | RRF gibrid qidiruvi orqali mos ko'rsatkichlar ID si, nomi, birligi va moslik reytingini qaytaradi. |
| `get_indicator_metadata` | `indicator_id: int` | 4 tildagi nomlar, birlik, metodika, mas'ul boshqarma, oxirgi yangilangan sana va klassifikator namunalari. |
| `get_data` | `indicator_id: int, item_codes: list[str] = None, periods: list[str] = None, limit: int = 500` | Faktik qiymatlar. `status = 'zero_marked'` bo'lgan qatorlar alohida ko'rsatiladi (tahlilni buzmaslik uchun). |
| `compare_regions` | `indicator_id: int, period: str` | Berilgan davr uchun viloyat va shaharlarni kamayish tartibida saralab solishtiradi. O'zbekiston Respublikasi benchmarki alohida ajratiladi. |
| `time_series` | `indicator_id: int, item_code: str` | Muayyan mahsulot yoki hududning butun davrlar bo'yicha dinamikasi, absolyut farq (`abs_change`) va o'sish foizini (`pct_change`) hisoblaydi. |
| `get_available_periods` | `indicator_id: int` | Ko'rsatkich bo'yicha bazada mavjud davrlar, minimal/maksimal davr va yillar ro'yxatini qaytaradi. |

---

## 4. MCP Serverni ishga tushirish va AI mijozlarga integratsiya

Server `stdio` (Claude Desktop va MCP Inspector uchun) hamda `sse` (veb-ilovalar uchun) transport rejimlarini qo'llab-quvvatlaydi:

```bash
# Standart stdio rejimi (CLI / Agentlar uchun)
python -m mcp_server.server

# SSE transport rejimi (Web ilovalar uchun)
python -m mcp_server.server --transport sse
```

### 4.1. MCP Inspector orqali sinovdan o'tkazish
Rasmiy MCP Inspector interfeysi orqali server asboblarini interaktiv tekshirish:
```bash
npx @modelcontextprotocol/inspector python -m mcp_server.server
```

### 4.2. Claude Desktop integratsiyasi
Claude Desktop sozlamalar fayliga (`claude_desktop_config.json`) quyidagi konfiguratsiya kiritiladi:
```json
{
  "mcpServers": {
    "siat-stat-uz": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "LOYIHA_ILDIZ_PAPKA_MANZILI",
      "env": {
        "DATABASE_URL": "postgresql://postgres:parol@localhost:5432/siat_dwh"
      }
    }
  }
}
```

---

## 5. Test va Verifikatsiya Natijalari

Avtomatlashtirilgan test to'plami:
```bash
python tests/test_mcp_tools.py
```

### Nazorat natijalari:
```text
===========================================================================
SIAT STAT DWH: MCP TOOLS TEST VA VERIFIKATSIYA SUITE
===========================================================================

[TEST 1/6] search_indicators: RRF Gibrid Qidiruv...
  * Qidiruv vaqti: 808.46 ms
  * Topilgan natijalar soni: 5 ta
  * 1-o'rindagi natija: #1308 - Bozorlar va do‘konlardagi ayrim tovarlarning o‘rtacha narxlari dinamikasi (Score: 0.016393)
  -> [OK] search_indicators testi muvaffaqiyatli o'tdi.

[TEST 2/6] get_indicator_metadata: Ko'rsatkich metama'lumotlari...
  * Ijro vaqti: 2.96 ms
  * Nomi (UZ): Bozorlar va do‘konlardagi ayrim tovarlarning o‘rtacha narxlari dinamikasi
  * Kodi: 1.11.03.0001
  * Birligi: 1 kg so‘mda
  * Jami klassifikatorlar soni: 41
  -> [OK] get_indicator_metadata testi muvaffaqiyatli o'tdi.

[TEST 3/6] get_data: Faktik qiymatlar va 1308 Benchmark Tekshiruvi...
  * Ijro vaqti: 15.07 ms
  * Qaytarilgan qatorlar: 1
  * Mahsulot: Mol go'shti (Kod: 017)
  * Davr: 2026-M09
  * Qiymat: 127,857.3 so'm (status: valid, zero_marked: False)
  -> [OK] get_data benchmark testi muvaffaqiyatli o'tdi (127857.3 == 127857.3).

[TEST 4/6] compare_regions: Hududlar reytingi (Ind #273, 2024)...
  * Ijro vaqti: 2.83 ms
  * Reytingdagi hududlar: 45 ta
  * Respublika ko'rsatkichi (Benchmark): 5.2
  * 1-o'rindagi hudud: Guliston shahri (Qiymat: 7.5)
  -> [OK] compare_regions testi muvaffaqiyatli o'tdi.

[TEST 5/6] time_series: Vaqt dinamikasi va o'sish sur'atlari (Ind #1308, '017')...
  * Ijro vaqti: 10.89 ms
  * Jami vaqt nuqtalari: 69 ta
  * Dastlabki davr: 2021-M01 -> 59081.6 so'm
  * Oxirgi davr: 2026-M09 -> 127857.3 so'm (O'sish: 1.6%)
  -> [OK] time_series testi muvaffaqiyatli o'tdi.

[TEST 6/6] get_available_periods: Mavjud davrlar tahlili...
  * Ijro vaqti: 6.03 ms
  * Jami davrlar: 69 ta
  * Davr oralig'i: 2021-M01 dan 2026-M09 gacha
  * Yillar: [2021, 2022, 2023, 2024, 2025, 2026]
  -> [OK] get_available_periods testi muvaffaqiyatli o'tdi.

===========================================================================
TEST NATIJALARI: 6/6 ta test to'liq muvaffaqiyatli o'tdi! (100%)
===========================================================================
```
