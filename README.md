# Aethelgard SIAT-STAT-UZ

O'zbekiston Davlat statistika qo'mitasi (SIAT/stat.uz) ma'lumotlari uchun Data Warehouse (DWH) va ETL infratuzilmasi.

---

## 📌 Loyiha Holati (Status)

| Bosqich | Vazifa | Holat | Izoh |
|---|---|---|---|
| **Day 1** | Xom ma'lumotlarni yig'ish va sifat auditi | ✅ 100% | Barcha datasetlar diskka olindi, anomaliyalar aniqlandi |
| **Day 2** | DWH arxitekturasi va ma'lumotlarni yuklash | 🔄 ~50% | Baza sxemalari va jadvallar tayyor, yuklash skripti qoldi |

---

## 📅 Day 1: Xom Ma'lumotlar Integratsiyasi (Bajarildi)

* **Yuklash natijasi:** 3 239 ta datasetdan **3 232 tasi (99.78%)** diskka muvaffaqiyatli saqlandi (qolgan 7 tasi stat.uz serverida bo'sh/404 xatolik bergani sababli tashlab ketildi).
* **Aniqlangan "tuzoqlar" va ularning yechimi:**
  * **Kirillcha «М» harfi (215 876 ta):** Sanalarda aralashib ketgan kirill harflari aniqlandi. Tahlil buzilmasligi uchun barchasi lotincha «M» ga o'tkaziladi.
  * **0.0 (Nol) qiymatlar (284 366 ta):** Mavsumiy yoki kiritilmagan bo'sh ma'lumotlar. Statistika ko'rsatkichini buzmasligi uchun tahliliy qismda `value = NULL`, holati esa `status = 'zero_marked'` deb belgilanadi.
  * **Davrlar xilma-xilligi:** Ma'lumotlar yillik (1.31M), oylik (1.08M) va choraklik (165K) davrlarga ajratildi.

---

## 📅 Day 2: DWH Arxitekturasi va Ingestion

### ✅ Qilingan ishlar (Baza poydevori tayyor):
1. **Sxemalar ajratildi:** `raw` (xom), `staging` (oraliq), `dwh` (asosiy ombor) va `mart` (analitika vitrinasi) sxemalari tuzildi.
2. **O'lcham jadvallari (Dimensions):**
   * `dim_indicator` — ko'rsatkichlar metama'lumotlari (nomlari, birliklari, chastotasi).
   * `dim_item` — klassifikatorlar (kod boshidagi nollar o'chib ketmasligi uchun qat'iy matn/`VARCHAR` formatida saqlanadi).
   * `dim_period` — vaqt davrlari (yil, chorak, oy tahlili uchun).
3. **Fakt jadvali (Facts):** `fact_value` jadvali takroriy yozilishning (dublikat) oldini oluvchi `UNIQUE` kaliti bilan qurildi.
4. **Tezkor qidiruv:** 3+ million qator ichidan so'zlarni soniyaning ulushida topish uchun `pg_trgm` va 15 ta `tsvector` GIN indekslari ulandi (`dwh/sql/schema.sql`).

### ⏳ Qolgan ishlar (Ertaga bajariladigan qism):
* [ ] `etl/load_dwh.py` transformatsiya skriptini yozish (JSON fayllarni o'qib, tozalab, bazaga quyuvchi modul).
* [ ] 10–20 ta datasetda sinov yuklashini (test run) o'tkazish.
* [ ] Barcha 3 232 ta faylni bazaga to'plamlab (batch `execute_values`) quyish (~20–25 daqiqa).
* [ ] Bazadagi umumiy qatorlar sonini tekshirish va qidiruv indekslarini validatsiya qilish.
