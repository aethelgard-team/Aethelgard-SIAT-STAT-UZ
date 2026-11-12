# Frontend Day 2: SSE Voqealarini UI'ga Ulash, Katalog va 2D Grafik

Barcha buyruqlar `frontend/` papkasida bajariladi.

## 1. Maqsad

Roadmap (7-bo'lim, 2-kun): **3D'siz ham to'liq ishlaydigan sayt.**
- Savol → javob → `[n]` manbalar oddiy HTML'da ishlaydi.
- "Bazada nima bor" sahifasi: katalog qidiruvi, ko'rsatkich sahifasi va 2D SVG grafik.
- Bosqichlarning 2D ko'rinishi — WebGL ishlamasa zaxira bo'ladi.

## 2. Backendga moslashtirish

Frontend `agent/orchestrator.py` dagi **haqiqiy** voqealarga moslab yozildi. Day 1 qoralamasidan farqlar:

| Joy | Qoralamada | Backendda (haqiqiy) |
|---|---|---|
| `generation.delta` | `text` | `delta` |
| `tool.called` | `args` | `arguments` |
| `verification.completed` | `sentences` | `checklist: [{text, passed, reason}]` |
| `tool` bosqichi | `stage.started/completed` | yo'q — `tool.called` ning o'zi belgi |
| MCP tool nomlari | `get_series`, `compute_change`, ... | `get_data`, `time_series`, `compare_regions`, ... |

`docs/sse-contract.md` shu farqlarga ko'ra yangilandi.

## 3. Yangi va o'zgargan fayllar

```
frontend/src/
├── main.js                ─── router: #/ask, #/catalog, #/indicator/{id}
├── api/client.js          ─── + getStats, searchIndicators, getIndicator, getSeries
├── core/format.js         ─── YANGI: raqam formati (127 857,3) va xavfsiz el() yordamchi
├── core/stages.js         ─── tool ro'yxati backenddagi 6 ta tool'ga moslandi
├── ui/askView.js          ─── YANGI: har bir SSE voqeasini ekranga ulash
├── ui/catalogView.js      ─── YANGI: "Bazada nima bor" va ko'rsatkich sahifasi
├── ui/stagesPanel.js      ─── + bosqich ostida haqiqiy tafsilot (ms, qatorlar, parametrlar)
└── viz/seriesChart.js     ─── YANGI: 2D SVG grafik
```

## 4. Savol sahifasi — voqealar qanday ko'rsatiladi

| Voqea | Ekranda |
|---|---|
| `stage.started` | Bosqich to'q sariq rangda yonadi |
| `stage.completed` (parse) | Til, qidiruv so'zi, davr, mahsulot kodi |
| `search.completed` | Topilgan ko'rsatkichlar ro'yxati RRF ballari bilan; tanlangani ajratiladi |
| `tool.called` | `get_data(indicator_id=1308, ...)`; 3D'da faqat shu tool tuguni yonadi |
| `stage.completed` (dwh) | `dwh.fact_value · 5 qator · 8.1 ms` |
| `tool.result` | Natija grafigi (2D) |
| `generation.delta` | Javob so'zma-so'z paydo bo'ladi |
| `verification.completed` | Har bir jumla: ✓ o'tdi yoki ✗ olib tashlandi (sababi bilan) |
| `done` | Faqat tekshiruvdan o'tgan javob + `[1]` manba havolasi va snapshot sanasi |
| `error` | Faol bosqichlar qizil, xato matni |

Maxsus holatlar:
- **Topilmadi** (`sources: []`) → "Bu haqda ma'lumot topilmadi" alohida rangda.
- **Oqim `done`siz tugasa** → xato sifatida ko'rsatiladi.
- **Yangi savol** → eski bosqichlar, grafik, manbalar va 3D holati tozalanadi.

## 5. "Bazada nima bor" sahifasi

- `/api/stats` — ko'rsatkichlar, klassifikator qatorlari, faktlar va yaroqli qiymatlar soni.
- `/api/indicators/search` — katalog qidiruvi; natija bosilsa ko'rsatkich sahifasi ochiladi.
- `/api/indicators/{id}` — kod, birlik, davriylik, mas'ul tashkilot, oxirgi o'zgarish, jamlanma belgisi.
- `/api/series` — tanlangan qator bo'yicha 2D grafik.

## 6. 2D grafik qoidalari

- `value = null` (`zero_marked`) bo'lgan davrda **chiziq uziladi** — yo'q qiymat chizilmaydi.
- Y o'qi haqiqiy minimum va maksimumga moslanadi (narx o'zgarishi ko'rinsin).
- Nuqta ustiga borilsa — aniq qiymat va davr.
- Bitta qiymat bo'lsa — grafik o'rniga katta raqam kartasi.
- Grafik ostida manba havolasi (siat.stat.uz, CC BY 4.0).

## 7. Tekshiruv

Backend hali lokal ishga tushirilmagani uchun, brauzerda backend formatidagi sinov oqimi bilan tekshirildi (sinov kodi loyihaga qo'shilmagan):

- [x] 7 ta bosqich ketma-ket yonadi, har birida haqiqiy tafsilot
- [x] 3D'da faqat `get_data` tuguni yonadi
- [x] Javob jonli yoziladi, `done` da tasdiqlangan javob bilan almashtiriladi
- [x] O'tmagan jumla ✗ va sababi bilan ko'rsatiladi
- [x] Grafikda `null` davr bo'sh qoldi (5 davrdan 4 ta nuqta)
- [x] "Topilmadi" holati to'g'ri ko'rinadi
- [x] Katalog → ko'rsatkich sahifasi → grafik ishlaydi
- [x] `npm run build` xatosiz

## 8. Qolgan ishlar

- [ ] Haqiqiy backend (`uvicorn api.main:app --port 8000`) bilan to'liq sinov — `.env` va baza kerak
- [ ] Day 3: 3D "Ombor" (DWH javonlari) va 3D ustunli grafik
- [ ] Day 4: inspektor panellari, demo rejim
