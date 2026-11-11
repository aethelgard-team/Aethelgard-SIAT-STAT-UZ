# Day 2: DWH Sxemasi, Arxitektura va Ingestion

## 📌 Joriy Holat: ~50%

### ✅ Bajarilgan ishlar (Poydevor va Sxema tayyor):
1. **Sxemalar:** PostgreSQL `siat_dwh` bazasida `raw`, `staging`, `dwh`, `mart` sxemalari ochildi.
2. **O'lcham jadvallari (Dimensions):**
   - `dwh.dim_indicator`: Ko'rsatkichlar metama'lumotlari.
   - `dwh.dim_item`: Klassifikatorlar (kodlar qat'iy matn/`VARCHAR` formatida).
   - `dwh.dim_period`: Davrlar iyerarxiyasi (yil, chorak, oy).
3. **Fakt jadvali (Facts):** `dwh.fact_value` jadvali takrorlanishdan himoyalovchi `UNIQUE` kaliti bilan qurildi.
4. **Tezkor qidiruv:** `pg_trgm` va 15 ta `tsvector` GIN indekslari sozlandi (`dwh/sql/schema.sql`).

### 🔄 Bajarilayotgan ishlar:
- [x] `etl/load_dwh.py` skriptining mantiqiy rejasini tasdiqlash.
- [ ] Transformatsiya va to'plamli yuklash skriptini yozish.
- [ ] 10 ta datasetda namunaviy sinov (1308-dataset tekshiruvi).
- [ ] 3 232 ta JSON faylni DWH ga to'liq quyish.
