# Frontend Day 3: 3D Sahna — Agent, Ombor (DWH) va 3D Grafik

Barcha buyruqlar `frontend/` papkasida bajariladi.

## 1. Maqsad

Roadmap (7-bo'lim, 3-kun): "AI ichida nima bo'lyapti"ni 3D'da ko'rsatish. Har bir 3D obyekt faqat backenddan kelgan **haqiqiy** ma'lumotni ko'rsatadi — bezak uchun narsa yo'q.

| Obyekt | Nimani ko'rsatadi | Ma'lumot manbai |
|---|---|---|
| **Agent** + 6 ta tool tuguni | AI qaysi MCP tool'ni chaqirdi | `tool.called` |
| Zarrachalar (Agent → tool) | Chaqiruv sodir bo'lgan payt | `tool.called` |
| **Ombor (DWH)** — qutilar | Bazada nechta ko'rsatkich bor | `GET /api/stats` → `total_indicators` |
| Yongan quti | Qidiruv tanlagan ko'rsatkich | `search.completed` → `selected_indicator_id` |
| **3D ustunli grafik** | Javobdagi raqamlar | `tool.result` → `data` |

## 2. Sahna tuzilishi

```
   Ombor (DWH)              Agent                 Natija (3D grafik)
  ┌───────────┐      ●  ●  (6 ta tool)  ●         ▐▐▐▐ ▐▐▐▐▐▐
  │ ▪▪▪▪▪▪▪▪▪ │          ◆  Agent                 ▐▐▐▐ ▐▐▐▐▐▐
  │ ▪▪▪▪▪▪▪▪▪ │      ●  ●               ●         ▐▐▐▐ ▐▐▐▐▐▐
  └───────────┘                                   (bo'shliq = qiymat yo'q)
     x = -7                x = 0                       x = +7
```

Kamera masofasi panel kengligiga qarab avtomatik hisoblanadi — uchala qism ham ekranga sig'adi.

## 3. Yangi va o'zgargan fayllar

```
frontend/src/
├── scene/agentScene.js   ─── qayta yozildi: 3 qism, HTML yorliqlar, zarrachalar, ma'lumot paneli
├── scene/warehouse.js    ─── YANGI: Ombor — InstancedMesh (3 232 quti bitta chizish chaqiruvida)
├── scene/bars3d.js       ─── YANGI: 3D ustunli grafik
├── main.js               ─── /api/stats → ombor
├── ui/askView.js         ─── search.completed → quti yonadi, tool.result → 3D ustunlar
├── style.css             ─── 3D yorliqlar va ma'lumot paneli
└── index.html            ─── #scene-labels, #scene-info
```

## 4. Roadmap qoidalari qanday bajarilgan

**Har bir yorliq — 3D nuqtaga bog'langan HTML tugma.** Tool nomlari va grafik ustunlari oddiy `<button>`: sichqoncha bilan ham, **Tab** tugmasi bilan ham tanlanadi. Har kadrda 3D koordinata ekran koordinatasiga aylantiriladi (`Vector3.project`).

**Ustun bosilganda** — aniq qiymat, davr, status, snapshot sanasi va manba havolasi. **Esc** yoki "Yopish" bilan yopiladi.

**Ustun balandligi = haqiqiy qiymat.** Balandlik `qiymat / eng katta qiymat` — 0 dan boshlanadi, shuning uchun ustunlar nisbati to'g'ri. `value = null` (`zero_marked`) bo'lgan davrda ustun chizilmaydi — faqat yerda kulrang belgi.

**Tool tuguni faqat haqiqiy `tool.called` bilan yonadi.** Backend `search_indicators` ni orkestrator ichida to'g'ridan-to'g'ri chaqiradi (`tool.called` yubormaydi), shuning uchun u tugun yonmaydi — faqat `get_data` yonadi.

**Kategoriya o'ylab topilmaydi.** `/api/stats` hozir faqat umumiy sonlarni beradi. Shuning uchun ombor **bitta blok** (3 232 quti) bo'lib turadi va qaysi quti #1308 ekani noma'lum — quti yonmaydi, faqat yorliqda `→ #1308` yoziladi. Backend kategoriyalarni bersa, javonlar avtomatik paydo bo'ladi (5-bo'lim).

**Kam harakat rejimi.** `prefers-reduced-motion` yoki `?quality=low` — aylanish, zarrachalar va animatsiya o'chadi, barcha ma'lumot va tugmalar ishlayveradi.

## 5. Backend uchun taklif (Siddiqqa)

Ombor javonlarga bo'linishi va topilgan ko'rsatkich qutisi yonishi uchun `/api/stats` javobiga ixtiyoriy `categories` maydoni kerak:

```json
"categories": [
  { "section": "1", "count": 600, "indicator_ids": [1001, 1002, ...] },
  { "section": "2", "count": 450, "indicator_ids": [...] }
]
```

SQL (bo'lim = `code` ning birinchi raqami, masalan `1.11.03.0001` → `1`):
```sql
SELECT split_part(code, '.', 1) AS section,
       count(*)                 AS count,
       array_agg(indicator_id ORDER BY indicator_id) AS indicator_ids
FROM dwh.dim_indicator
GROUP BY 1
ORDER BY 1;
```

Frontend bu maydonni allaqachon qo'llab-quvvatlaydi — maydon bo'lmasa ham ishlaydi.

## 6. Tekshiruv

Backend lokal ishga tushirilmagani uchun, Siddiqning javob formatini aynan takrorlaydigan **vaqtinchalik sinov serveri** (8000-portda, loyihaga qo'shilmagan) bilan haqiqiy SSE yo'li orqali tekshirildi:

- [x] `/health` → "Backend: ulangan"; `/api/stats` → "Ombor (DWH): 3 232 ko'rsatkich"
- [x] Savol berilganda faqat `get_data` tuguni yonadi, zarrachalar uchadi
- [x] 12 ta davr → 12 ta ustun, `null` oy bo'sh qoldi
- [x] Oxirgi ustun bosildi → "127 857,3 so'm/kg · 2026-M09 · status: valid · snapshot: 2026-11-11 · Manba"
- [x] `categories` bilan: 6 ta javon o'z soni bilan, #1308 qutisi yondi
- [x] Backend o'chiq: "Ombor (DWH): mavjud emas" — qutilar chizilmaydi
- [x] Yangi savol: tool, quti, ustunlar va panel tozalanadi
- [x] `npm run build` xatosiz

## 7. Qolgan ishlar

- [ ] Haqiqiy backend bilan to'liq sinov (`.env` va baza kerak)
- [ ] Siddiq bilan `categories` maydonini kelishish
- [ ] Day 4: inspektor panellari (har bir tugun uchun), WebGL'siz 2D rejim, demo rejim
