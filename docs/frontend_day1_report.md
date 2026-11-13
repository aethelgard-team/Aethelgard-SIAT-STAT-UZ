# Frontend Day 1: Loyiha Skeleti va SSE Shartnomasi

Barcha buyruqlar `frontend/` papkasida bajariladi.

## 1. Maqsad

Roadmap (7-bo'lim, 1-kun) bo'yicha frontendning birinchi kuni ikki natija beradi:
1. Backend bilan **SSE voqealari va API javob shakllari** kelishib olinadi — shundan keyin frontend va backend parallel ishlay oladi.
2. **Vite + Three.js + GSAP** loyihasi ishga tushadi, bosqichlar jadvali tayyorlanadi.

## 2. Texnologiyalar

| Qatlam | Texnologiya | Nima uchun |
|---|---|---|
| Build / dev server | Vite 8 | Tez ishga tushadi, `/api` so'rovlarini backendga proxy qiladi |
| 3D sahna | Three.js | "Agent" va MCP tool tugunlarini 3D'da ko'rsatish |
| Animatsiya | GSAP | Tool chaqirilganda tugunni yondirish |
| Til | Vanilla JavaScript (ES modules) | Framework'siz — o'rganish va tushunish oson |

Ishga tushirish:
```bash
npm install
npm run dev
```
Sayt: `http://localhost:5173`

## 3. Papkalar tuzilmasi

```
frontend/
├── index.html
├── vite.config.js        ─── /api va /health → http://localhost:8000 (FastAPI)
└── src/
    ├── main.js           ─── kirish nuqtasi
    ├── style.css
    ├── api/client.js     ─── backend bilan aloqa (fetch + SSE oqimini o'qish)
    ├── core/stages.js    ─── 7 ta bosqich va 6 ta MCP tool ro'yxati
    ├── scene/agentScene.js ─ 3D sahna: Agent + 6 ta tool tuguni
    ├── ui/stagesPanel.js ─── bosqichlarning 2D ro'yxati
    └── viz/              ─── grafiklar (Day 2+)
```

## 4. Bosqichlar jadvali

| Bosqich | Tomoshabin savoli | Ma'lumot (SSE voqea) |
|---|---|---|
| `parse` — Savolni tahlil | AI nimani tushundi? | `stage.completed` (til, normallashtirilgan so'rov) |
| `search` — Katalogdan qidirish | Qaysi ko'rsatkichlar topildi? | `search.completed` (RRF natijalari) |
| `tool` — MCP tool chaqiruvi | AI qaysi asbobni chaqirdi? | `tool.called` |
| `dwh` — DWH'dan o'qish | Raqam qayerdan keldi? | `stage.completed` (jadval, qatorlar soni, ms) |
| `result` — Natija | Raqamlar qanday? | `tool.result` |
| `generate` — Javob yozish | Model nima yozyapti? | `generation.delta` |
| `verify` — Tekshirish | Har bir jumlaga ishonsa bo'ladimi? | `verification.completed` |

## 5. SSE shartnomasi

Qoralama `docs/sse-contract.md` da yozildi va backend dasturchiga 3 ta savol berildi:

| Savol | Backend javobi |
|---|---|
| FastAPI qaysi portda? | `8000`, CORS `5173` uchun ochiq |
| `tool.result.data` da qatorlar to'liq keladimi? | Ha, barcha qatorlar keladi |
| 7 ta `stage` nomi mosmi? | Ha: `parse → search → tool → dwh → result → generate → verify → done` |

Holat: **kelishilgan**.

## 6. Roadmap qoidalari qanday bajarilgan

- **Har bir raqam backenddan keladi.** Backend javob bermasa, sahifada "Mavjud emas" yoziladi — hech narsa o'ylab topilmaydi.
- **Matn faqat `textContent` bilan qo'yiladi**, `innerHTML` ishlatilmaydi.
- **WebGL bo'lmasa** 3D o'rniga ogohlantirish chiqadi, 2D bosqichlar ro'yxati ishlayveradi.
- **`prefers-reduced-motion`** yoki `?quality=low` bo'lsa, 3D aylanish va animatsiya o'chadi.

## 7. Tekshiruv

- [x] `npm run dev` ishga tushadi, sahifa ochiladi
- [x] `npm run build` xatosiz o'tadi
- [x] 3D sahna markazda, Agent atrofida 6 ta tool tuguni
- [x] Backend o'chiq bo'lsa: "Backend: mavjud emas" va savolga "Mavjud emas — backend javob bermadi."
- [x] SSE shartnomasi backend bilan kelishildi

**Tuzatilgan xato:** yuqori piksel zichligidagi ekranlarda (DPR 1.5) 3D sahna chetga surilib qolardi — `renderer.setSize(w, h)` bilan tuzatildi.
