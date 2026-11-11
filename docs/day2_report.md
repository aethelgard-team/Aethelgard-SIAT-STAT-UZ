# Day 2: DWH arxitekturasi va ma'lumotlarni ommaviy yuklash (Bulk Ingestion)

## 1. Infratuzilma va DDL sxemalar

Ma'lumotlar bazasi: PostgreSQL (`siat_dwh`).
Sxemani yaratish:
```bash
psql -U postgres -d siat_dwh -f dwh/sql/schema.sql
```

Sxema arxitekturasi:
- `raw`: Xom SDMX fayllar va oraliq ma'lumotlar uchun
- `staging`: Tozalash va deduplikatsiya bosqichi
- `dwh`: Yulduzsimon (Star schema) ombor qatlami
- `mart`: Analitik agregatsiyalar va vitrinalar

Jadvallar tuzilishi:
| Jadval nomi | Turi | Tavsifi |
|---|---|---|
| `dwh.dim_indicator` | Dimension | Ko'rsatkich metama'lumotlari (nomlar, o'lchov birligi, davriylik) |
| `dwh.dim_item` | Dimension | Klassifikatorlar (kodlar VARCHAR formatida, bosh nollar saqlangan) |
| `dwh.dim_period` | Dimension | Standartlashtirilgan davrlar (yil, chorak, oy) |
| `dwh.fact_value` | Fact | Statistik qiymatlar (value, raw_value, snapshot_date, status) |

Optimallashtirish va qidiruv:
- `pg_trgm` kengaytmasi faollashtirildi
- Trigram indekslar va 15 ta `tsvector` GIN to'liq matnli qidiruv indekslari o'rnatildi
- Takrorlanishning oldini olish: `UNIQUE(indicator_id, item_id, period_key, snapshot_date)`

## 2. ETL transformatsiya va yuklash

To'plamli yuklash skriptini ishga tushirish:
```bash
# 10 ta datasetda namunaviy test
python etl/load_dwh.py --limit 10

# Barcha 3 232 ta faylni to'liq yuklash (batch size: 5000)
python etl/load_dwh.py
```

Ijro ko'rsatkichlari (Execution stats):
- Qayta ishlangan JSON fayllar: 3 232 ta (100.0%)
- Jami yozilgan faktlar (`fact_value`): 2 580 045 qator
- Klassifikatorlar soni (`dim_item`): 131 587 ta
- Ko'rsatkichlar soni (`dim_indicator`): 3 232 ta
- Tozalangan kirill 'М' davrlari: 215 876 ta
- Normallashtirilgan 0.0 qiymatlar (`zero_marked`): 284 209 ta
- Umumiy sarflangan vaqt: 241.97 soniya (~4 daqiqa)

## 3. Baza verifikatsiyasi va yaxlitlik tekshiruvi

PostgreSQL'da bajarilgan nazorat so'rovi:
```sql
SELECT 
    (SELECT count(*) FROM dwh.dim_indicator) AS indicators_count,
    (SELECT count(*) FROM dwh.dim_item) AS items_count,
    (SELECT count(*) FROM dwh.fact_value) AS total_facts,
    (SELECT count(*) FROM dwh.fact_value WHERE status = 'zero_marked') AS zero_marked_facts;
```

Amaldagi natija:
```text
 indicators_count | items_count | total_facts | zero_marked_facts 
------------------+-------------+-------------+-------------------
             3232 |      131587 |     2580045 |            284209
```

Roadmap bo'yicha aniq qiymat tekshiruvi:
```sql
SELECT i.indicator_id, it.item_code, it.name_uz, f.period_key, f.value, f.status
FROM dwh.fact_value f
JOIN dwh.dim_indicator i ON f.indicator_id = i.indicator_id
JOIN dwh.dim_item it ON f.item_id = it.item_id
WHERE i.indicator_id = 1308 AND it.item_code = '017' AND f.period_key = '2026-M09';
```

Natija: `127857.3000` (Status: `valid`, SIAT rasmiy statistikasiga 100% mos).
