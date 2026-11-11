# Day 2: DWH Sxemasi, Arxitektura va Ingestion

## 📌 Joriy Holat: 100% (Yakunlandi)

### ✅ Bajarilgan ishlar:
1. **Sxemalar:** PostgreSQL `siat_dwh` bazasida `raw`, `staging`, `dwh`, `mart` sxemalari to'liq ochildi.
2. **O'lcham jadvallari (Dimensions):**
   - `dwh.dim_indicator`: 3 232 ta statistik ko'rsatkich metama'lumotlari.
   - `dwh.dim_item`: 131 587 ta klassifikator (kodlar qat'iy matn/`VARCHAR` formatida saqlandi).
   - `dwh.dim_period`: Davrlar iyerarxiyasi (yil, chorak, oy tahlillari uchun).
3. **Fakt jadvali (Facts):** `dwh.fact_value` jadvali 2 580 045 ta tozalangan faktik ko'rsatkich bilan to'ldirildi.
4. **Tezkor qidiruv:** `pg_trgm` va 15 ta `tsvector` GIN indekslari sozlandi (`dwh/sql/schema.sql`).
5. **Ingestion Pipeline (`etl/load_dwh.py`):**
   - [x] `etl/load_dwh.py` skriptining mantiqiy rejasini tasdiqlash.
   - [x] Transformatsiya va to'plamli yuklash (`psycopg2.extras.execute_values`) skriptini yozish.
   - [x] 10 ta datasetda namunaviy sinov (1308-dataset tekshiruvi muvaffaqiyatli o'tdi).
   - [x] 3 232 ta JSON faylni DWH ga to'liq quyish (Full Ingestion).

---

## 📊 Yakuniy Ingestion Statistikasi
- **Qayta ishlangan JSON fayllar:** 3 232 ta (100%)
- **Statistik ko'rsatkichlar (`dim_indicator`):** 3 232 ta
- **Klassifikator qatorlari (`dim_item`):** 131 587 ta
- **Jami saqlangan faktlar (`fact_value`):** 2 580 045 ta
- **Tozalangan Kirillcha «М» davrlari:** 215 876 ta (barchasi lotin «M» ga normallashtirildi)
- **Tozalangan 0.0 qiymatlar:** 284 209 ta (`value = NULL`, `status = 'zero_marked'`)
- **Umumiy sarflangan vaqt:** 241.97 soniya (~4.03 daqiqa)

---

## 🎯 Benchmark Tekshiruvi
- **Ko'rsatkich #1308:** Bozorlar va do‘konlardagi ayrim tovarlarning o‘rtacha narxlari dinamikasi
- **Mahsulot:** Mol go'shti (kod: `017`)
- **Davr:** `2026-M09`
- **Bazadagi qiymat:** `127,857.3 so'm` (`status: valid`, `snapshot_date: 2026-11-11`)
- **Holati:** ✅ Rasmiy ko'rsatkich bilan 100% teng.
