# Frontend Day 4: Inspektorlar va zaxira rejimlar

Barcha buyruqlar `frontend/` papkasida bajariladi.

## 1. Maqsad

Roadmap (7-bo'lim, 4-kun):
1. Har bir tugun bosilganda panel ochilsin — o'sha bosqichning **haqiqiy** ma'lumoti (parametrlar, qatorlar soni, vaqt). Esc yopadi, fokus qaytadi.
2. WebGL yo'q → 2D ko'rinish; `prefers-reduced-motion` yoki `?quality=low` → animatsiyasiz, lekin hamma funksiya ishlaydi.
3. Demo rejim: bitta haqiqiy, to'g'ri javob yozib olinadi.
4. Matn faqat `textContent` bilan.

## 2. Yangi va o'zgargan fayllar

```
frontend/
├── src/ui/inspector.js    ─── YANGI: inspektor oynasi (<dialog>)
├── src/scene/scene2d.js   ─── YANGI: WebGL'siz 2D sahna (3D bilan bir xil API)
├── src/api/demo.js        ─── YANGI: demo yozuvini yuklash, qayta ijro, saqlash
├── public/demo/README.md  ─── YANGI: demo.json qanday olinadi
├── src/ui/askView.js      ─── voqealar jurnali, inspektor, demo
├── src/ui/stagesPanel.js  ─── har bosqichda "Batafsil" tugmasi
├── src/scene/agentScene.js─── tool yorlig'i bosilsa inspektor
├── src/main.js            ─── 3D / 2D / demo rejimini tanlash
├── src/style.css          ─── inspektor, 2D, demo banner
└── index.html             ─── #inspector, #demo-banner, #save-demo
```

## 3. Inspektor

| Qayerni bosasiz | Nima chiqadi |
|---|---|
| Bosqichdagi **Batafsil** | Shu bosqichga tegishli barcha SSE voqealari, har birining vaqti (`+234 ms`) va maydonlari |
| 3D (yoki 2D) dagi **tool nomi** | `tool.called` (parametrlar) + o'sha `call_id` li `tool.result` |
| Chaqirilmagan tool | "Bu savolda bu tool chaqirilmagan." |

- Faqat backend yuborgan maydonlar ko'rsatiladi. Katta ro'yxatlar (masalan 12 qator) — soni va birinchi elementi.
- `generation.delta` lar bittaga jamlanadi: nechta bo'lak va matn uzunligi.
- **Esc** yoki "Yopish" — yopiladi, fokus bosilgan tugmaga qaytadi.

## 4. 2D rejim

WebGL yo'q bo'lsa — avtomatik; sinash uchun: `http://localhost:5173/?mode=2d`

- 6 ta tool — tugmalar ro'yxati, chaqirilgani yonadi, bosilsa inspektor.
- Ombor: `Ombor (DWH): 3 232 ko'rsatkich → #1308`
- Natija pastdagi 2D SVG grafikda.

Kam harakat rejimi (`prefers-reduced-motion`, `?quality=low`) 3-kundan beri ishlaydi.

## 5. Demo rejim

`http://localhost:5173/?demo=1`

- Tepada doimiy sariq banner: **"DEMO — yozib olingan haqiqiy javob (sana)"**.
- Savol maydoni yozuvdagi savol bilan to'ladi, o'zgartirib bo'lmaydi.
- **Backendga so'rov yuborilmaydi** — voqealar yozilgan vaqt oralig'i bilan qayta ijro etiladi.
- Yozuv yo'q bo'lsa: "DEMO — yozuv topilmadi" — hech narsa o'ylab topilmaydi.

**Yozuvni olish (haqiqiy backend kerak):**
1. Jonli rejimda savol bering, javob manbasi bilan chiqsin.
2. Raqamni siat.stat.uz dagi bilan solishtiring.
3. **"Demo uchun saqlash (demo.json)"** tugmasi → faylni `frontend/public/demo/` ga qo'ying.

Tugma faqat manbali to'liq javobdan keyin chiqadi.

## 6. Tekshiruv

Backend javob formatini takrorlaydigan **vaqtinchalik sinov serveri** bilan (loyihaga qo'shilmagan):

- [x] 7 ta bosqichda "Batafsil" bor; DWH → `table: dwh.fact_value · rows_count: 12 · execution_ms: 8.1`
- [x] Esc yopdi, fokus "DWH'dan o'qish" tugmasiga qaytdi
- [x] `get_data` → parametrlar `indicator_id: 1308, item_codes: ["017"]` va natija; `compare_regions` → "chaqirilmagan"
- [x] `?mode=2d`: canvas yo'q, 6 tool ro'yxati, `get_data` yondi, inspektor ochildi, 2D grafik bor
- [x] `?demo=1` yozuv bilan: banner, javob "done", `/api/ask` so'rovlari = **0**
- [x] `?demo=1` yozuvsiz: "yozuv topilmadi"
- [x] Sinov yozuvi o'chirildi — `public/demo/` da faqat README
- [x] Konsolda xato yo'q, `npm run build` xatosiz

## 7. Qolgan ishlar

- [ ] Haqiqiy backend bilan sinov va **haqiqiy** `demo.json` yozib olish (`.env` va baza kerak)
- [ ] Siddiq bilan `categories` maydonini kelishish
- [ ] Day 5: Playwright testlari, 390 / 1440 / 1920 px skrinshotlar, README
