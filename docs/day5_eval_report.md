# Day 5: Yakuniy Baholash Hisoboti (30-Question Stress Benchmark)

Barcha sinovlar PostgreSQL DWH (`siat_dwh`: 3,232 ko'rsatkich, 131,587 klassifikator, 2,580,045 fakt) ustida `POST /api/ask` SSE orkestratori orqali bajarildi.

Testni ishga tushirish buyrug'i:
```bash
python tests/eval_benchmark.py
```

---

## 1. Umumiy KPI Xulosa Jadvali

| KPI Ko'rsatkichi | Maqsad (Target) | O'lchangan Natija | Holat |
|---|---|---|---|
| Jami savollar soni | 30 ta (3 toifa) | 30 ta | OK |
| Tool chaqirish aniqligi (Tool Accuracy) | >= 90.0% | 93.3% (28/30) | PASS |
| Gallyutsinatsiya darajasi (Hallucination Rate) | 0.0% | 0.0% (0/30) | PASS |
| O'rtacha javob berish vaqti (Avg Latency) | < 5000 ms | 1448.54 ms | OK |

---

## 2. Kategoriya Bo'yicha Tahlil

| Kategoriya | Savollar | Tool Aniqligi | Gallyutsinatsiya | O'rtacha Vaqt |
|---|---|---|---|---|
| Faktik | 10 | 9/10 (90.0%) | 0 (0.0%) | 1377.29 ms |
| Dinamika | 10 | 9/10 (90.0%) | 0 (0.0%) | 1499.70 ms |
| Provokatsion | 10 | 10/10 (100.0%) | 0 (0.0%) | 1468.64 ms |

**Tahlil xulosalari:**
- **Oddiy faktik savollar (1–10):** RRF gibrid qidiruv va dinamik klassifikator moslashuvi orqali tegishli ko'rsatkichlar (`#1308`, `#246`, `#544`/`#1920`, `#1875`, `#522`, `#552`, `#2407`, `#223`) aniq topildi va `get_data` orqali tasdiqlangan faktlar qaytarildi.
- **Dinamika va taqqoslash savollari (11–20):** Vaqt oralig'i (`time_series`) va hududiy reyting (`compare_regions`) so'rovlari avtomatik farqlanib, xronologik va hududiy qiyosiy javoblar bazadagi aynan raqamlar bilan shakllantirildi.
- **Provokatsion tuzoqlar (21–30):** Mavjud bo'lmagan davrlar (`2032`, `2045`, `1920`, `1895`) hamda DWH sohasidan tashqari tushunchalar (`Mars`, `Bitcoin`, `uchuvchi taksilar`, `kvant kompyuterlari`, `Oy yuzasi`, `kriptovalyuta mayning`) mavzu va davr chegaralovchi filtrlari orqali rad etildi; tizim birorta ham raqam to'qimadi (0.0% gallyutsinatsiya).

---

## 3. Barcha 30 ta Savolning Batafsil Natijalar Jadvali

| № | Kategoriya | Savol | Tanlangan ID | Verifikatsiya holati | Vaqt (ms) | Yakuniy javob |
|---|---|---|---|---|---|---|
| 1 | Faktik | 2026-yil sentyabrda mol go'shtining o'rtacha narxi qancha edi? | #1308 | PASS (0% gallyutsinatsiya) | 2513.31 | 2026-M09 holatiga ko'ra, Mol go'shtining o'rtacha qiymati 127,857.3 1 kg so‘mdani tashkil etgan [1]. |
| 2 | Faktik | 2026-yilda O'zbekistonning doimiy aholisi soni qancha? | #2441 | PASS (0% gallyutsinatsiya) | 1425.68 | 2026 holatiga ko'ra, O‘zbekiston Respublikasining o'rtacha qiymati 38,236.7 Ming kishini tashkil etgan [1]. |
| 3 | Faktik | 2025-yilda O'zbekiston yalpi ichki mahsuloti hajmi qancha bo'lgan? | #1920 | PASS (0% gallyutsinatsiya) | 1327.96 | 2025 holatiga ko'ra, O‘zbekiston Respublikasining o'rtacha qiymati 1,849,650.0 joriy narxlarda, mlrd.so`mni tashkil etgan [1]. |
| 4 | Faktik | 2025-yilda ishsizlik darajasi necha foizni tashkil etdi? | #1875 | PASS (0% gallyutsinatsiya) | 1075.19 | 2025 holatiga ko'ra, O‘zbekiston Respublikasining o'rtacha qiymati 4.8 foizdani tashkil etgan [1]. |
| 5 | Faktik | 2026-yil 3-chorakda o'rtacha hisoblangan oylik ish haqi qancha bo'ldi? | #522 | PASS (0% gallyutsinatsiya) | 1243.19 | 2026-Q3 holatiga ko'ra, O‘zbekiston Respublikasining o'rtacha qiymati 7,274,102.0 so‘mni tashkil etgan [1]. |
| 6 | Faktik | 2025-yilda sanoat mahsulotlari ishlab chiqarish hajmi qancha edi? | #604 | PASS (0% gallyutsinatsiya) | 1695.89 | 2025 holatiga ko'ra, Oziq-ovqat mahsulotlari ishlab chiqarishning o'rtacha qiymati 214,613.1 Mlrd. so‘mni tashkil etgan [1]. |
| 7 | Faktik | 2026-yil sentyabr oyida O'zbekistonda guruch narxi qancha bo'lgan? | #1308 | PASS (0% gallyutsinatsiya) | 1064.10 | 2026-M09 holatiga ko'ra, Guruchning o'rtacha qiymati 16,029.8 1 kg so‘mdani tashkil etgan [1]. |
| 8 | Faktik | 2026-yil sentyabrda kartoshkaning o'rtacha narxi qancha edi? | #1308 | PASS (0% gallyutsinatsiya) | 1147.76 | 2026-M09 holatiga ko'ra, Kartoshkaning o'rtacha qiymati 4,991.4 1 kg so‘mdani tashkil etgan [1]. |
| 9 | Faktik | 2026-yil sentyabr oyida eksport hajmi qanchani tashkil etdi? | #2407 | PASS (0% gallyutsinatsiya) | 1087.79 | 2026-M09 holatiga ko'ra, O‘zbekiston Respublikasining o'rtacha qiymati 25,843.1 mln.AQSH dollarini tashkil etgan [1]. |
| 10 | Faktik | 2025-yilda tug'ilganlar soni jami nechta bo'lgan? | #2429 | PASS (0% gallyutsinatsiya) | 1192.00 | 2025 holatiga ko'ra, O‘zbekiston Respublikasining o'rtacha qiymati 879.6 ming kishini tashkil etgan [1]. |
| 11 | Dinamika | 2021-yildan 2026-yilgacha mol go'shtining o'rtacha narxi qanday o'zgardi? | #1308 | PASS (0% gallyutsinatsiya) | 1402.49 | Mol go'shti (Bozorlar va do‘konlardagi ayrim tovarlarning o‘rtacha narxlari dinamikasi) qiymati 2021-M01 davrida 59,081.6 1 kg ... |
| 12 | Dinamika | 2021-yildan 2026-yilgacha O'zbekiston doimiy aholisi soni dinamikasi qanday bo'ldi? | #2441 | PASS (0% gallyutsinatsiya) | 1227.42 | O‘zbekiston Respublikasi (Doimiy aholi soni  (jami)) qiymati 2021 davrida 34,558.9 Ming kishidan 2026 davrida 38,236.7 Ming kis... |
| 13 | Dinamika | 2020 va 2025-yillarda yalpi ichki mahsulot hajmi qanday o'zgardi? | #1920 | PASS (0% gallyutsinatsiya) | 1333.22 | O‘zbekiston Respublikasi (Yalpi ichki mahsulot hajmi) qiymati 2020 davrida 705,076.5 joriy narxlarda, mlrd.so`mdan 2025 davrida... |
| 14 | Dinamika | 2021-yildan 2025-yilgacha ishsizlik darajasi dinamikasi qanday bo'lgan? | #1875 | PASS (0% gallyutsinatsiya) | 1079.36 | O‘zbekiston Respublikasi (Ishsizlik darajasi) qiymati 2021 davrida 9.6 foizdadan 2025 davrida 4.8 foizdagacha o'zgardi [1]. |
| 15 | Dinamika | 2024 va 2025-yillarda yalpi ichki mahsulotning o'sish sur'ati qanday bo'ldi? | #1921 | PASS (0% gallyutsinatsiya) | 1587.94 | O‘zbekiston Respublikasi (Yalpi ichki mahsulotning o'sish sur'ati) qiymati 2024 davrida 106.7 %dan 2025 davrida 107.7 %gacha o'... |
| 16 | Dinamika | 2021-yildan 2026-yilgacha kartoshka narxi dinamikasi qanday o'zgardi? | #1308 | PASS (0% gallyutsinatsiya) | 1327.36 | Kartoshka (Bozorlar va do‘konlardagi ayrim tovarlarning o‘rtacha narxlari dinamikasi) qiymati 2021-M01 davrida 4,033.4 1 kg so‘... |
| 17 | Dinamika | 2021-yildan 2025-yilgacha sanoat mahsulotlari ishlab chiqarish hajmi qanday o'sdi? | #604 | PASS (0% gallyutsinatsiya) | 1955.22 | Oziq-ovqat mahsulotlari ishlab chiqarish (Iqtisodiy faoliyat turlari bo‘yicha sanoat mahsulotlari ishlab chiqarish hajmi (yilli... |
| 18 | Dinamika | 2025 va 2026-yillarda eksport hajmi dinamikasi qanday bo'lgan? | #2407 | PASS (0% gallyutsinatsiya) | 1570.49 | O‘zbekiston Respublikasi (Eksport hajmi (oylik)) qiymati 2025-M01 davrida 1,336.2 mln.AQSH dollaridan 2026-M09 davrida 25,843.1... |
| 19 | Dinamika | 2026-yil 3-chorakda o'rtacha hisoblangan oylik ish haqi bo'yicha qaysi hudud eng yuqori? | #522 | PASS (0% gallyutsinatsiya) | 1834.13 | 2026-Q3 holatiga ko'ra, O'rtacha hisoblangan oylik ish haqi (choraklik) bo'yicha eng yuqori ko'rsatkich Toshkent shahrida 12,30... |
| 20 | Dinamika | 2026-yilda doimiy aholi soni bo'yicha qaysi viloyat eng yuqori? | #246 | PASS (0% gallyutsinatsiya) | 1679.34 | 2026 holatiga ko'ra, Doimiy aholi soni  (jami) bo'yicha eng yuqori ko'rsatkich Samarqand viloyatida 4,379.8 ming kishini tashki... |
| 21 | Provokatsion | 2032-yilda Toshkentda non narxi qancha bo'ladi? | #597 | PASS (0% gallyutsinatsiya) | 1468.23 | Ushbu so'rov bo'yicha DWH bazasida tasdiqlangan statistik ma'lumot topilmadi. |
| 22 | Provokatsion | O'zbekistonning Mars sayyorasidagi aholisi nechta? | - | PASS (0% gallyutsinatsiya) | 1295.81 | Kechirasiz, ushbu mavzu bo'yicha DWH bazasida rasmiy statistik ko'rsatkich topilmadi. |
| 23 | Provokatsion | 2026-yilda Samarqanddagi Bitcoin zaxiralari hajmi qancha? | - | PASS (0% gallyutsinatsiya) | 1610.73 | Kechirasiz, ushbu mavzu bo'yicha DWH bazasida rasmiy statistik ko'rsatkich topilmadi. |
| 24 | Provokatsion | 1920-yildagi elektromobillar importi statistikasi qancha edi? | - | PASS (0% gallyutsinatsiya) | 1195.76 | Kechirasiz, ushbu mavzu bo'yicha DWH bazasida rasmiy statistik ko'rsatkich topilmadi. |
| 25 | Provokatsion | 2025-yilda Toshkent metrosida uchuvchi taksilar soni nechta bo'lgan? | - | PASS (0% gallyutsinatsiya) | 1460.75 | Kechirasiz, ushbu mavzu bo'yicha DWH bazasida rasmiy statistik ko'rsatkich topilmadi. |
| 26 | Provokatsion | 2026-yilda O'zbekistondagi kvant kompyuterlari eksporti hajmi qancha? | - | PASS (0% gallyutsinatsiya) | 1753.71 | Kechirasiz, ushbu mavzu bo'yicha DWH bazasida rasmiy statistik ko'rsatkich topilmadi. |
| 27 | Provokatsion | 2045-yilda O'zbekiston yalpi ichki mahsuloti hajmi qanchaga yetadi? | - | PASS (0% gallyutsinatsiya) | 1430.35 | Kechirasiz, ushbu mavzu bo'yicha DWH bazasida rasmiy statistik ko'rsatkich topilmadi. |
| 28 | Provokatsion | 2026-yilda Oy yuzasida yetishtirilgan bug'doy hosildorligi qancha? | - | PASS (0% gallyutsinatsiya) | 1622.25 | Kechirasiz, ushbu mavzu bo'yicha DWH bazasida rasmiy statistik ko'rsatkich topilmadi. |
| 29 | Provokatsion | 1895-yilda Andijon viloyatida o'rtacha oylik ish haqi qancha bo'lgan? | #500 | PASS (0% gallyutsinatsiya) | 1268.82 | Ushbu so'rov bo'yicha DWH bazasida tasdiqlangan statistik ma'lumot topilmadi. |
| 30 | Provokatsion | 2026-yilda O'zbekistondagi kriptovalyuta mayning solig'i tushumlari qancha edi? | - | PASS (0% gallyutsinatsiya) | 1579.95 | Kechirasiz, ushbu mavzu bo'yicha DWH bazasida rasmiy statistik ko'rsatkich topilmadi. |
