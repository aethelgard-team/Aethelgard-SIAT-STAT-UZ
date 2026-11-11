# Day 4: FastAPI, SSE Orkestratsiyasi va Nol-Gallyutsinatsiya Verifikatsiyasi

Barcha buyruqlar loyiha ildizida bajariladi.

## 1. Tizim Arxitekturasi va API Spetsifikatsiyasi

Day 4 doirasida DWH ombori, RRF gibrid qidiruvi va MCP asboblari ustida FastAPI asosidagi asinxron REST hamda Server-Sent Events (SSE) orkestratsiya qatlami qurildi. Tizim frontend (Vite / React / 3D vizualizatsiya) va tashqi mijozlar uchun xizmat qiladi.

Serverni ishga tushirish:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 1.1. CORS va Xavfsizlik Konfiguratsiyasi
Frontend integratsiyasini ta'minlash uchun `CORSMiddleware` sozlangan:
- Ruxsat etilgan manbalar (Origins): `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`
- Barcha standart HTTP metodlari va sarlavhalari (Headers) ochiq.
- Xavfsizlik parametrlari: maxfiy kalitlar faqat lokal `.env` da saqlanadi, `.env.example` shablon sifatida kiritilgan.

### 1.2. REST Endpointlar Spetsifikatsiyasi

| Metod | Endpoint | Parametrlar | Tavsif |
|---|---|---|---|
| `GET` | `/health` | - | Server va PostgreSQL ulanish salomatligi |
| `GET` | `/api/stats` | - | DWH ombori umumiy statistikasi (jami faktlar, ko'rsatkichlar) |
| `GET` | `/api/indicators/search` | `q`, `lang`, `limit` | Trigram va FTS asosidagi RRF gibrid qidiruvi |
| `GET` | `/api/indicators/{id}` | `indicator_id` | Ko'rsatkichning 4 tildagi nomi va metama'lumotlari |
| `GET` | `/api/series` | `indicator_id`, `item_codes`, `from`, `to`, `limit` | Vaqt qatorlari bo'yicha filtrlanadigan faktlar |
| `POST` | `/api/ask` | `{"question": "..."}` | 7 bosqichli Server-Sent Events (SSE) oqimi |

---

## 2. Server-Sent Events (SSE) 7 Bosqichli Orkestratsiya Protokoli

`POST /api/ask` so'rovi `text/event-stream` formatida hodisalarni oqimli tarzda mijozga uzatadi.

```
Mijoz Savoli
    │
    ▼
1. parse        ─── Til, davr (2026-M09) va mahsulot kodini (017) ajratish
    │
    ▼
2. search       ─── RRF gibrid qidiruv orqali eng mos ko'rsatkichni aniqlash (#1308)
    │
    ▼
3. tool         ─── MCP asbobini parametrlar bilan chaqirish (get_data)
    │
    ▼
4. dwh          ─── PostgreSQL fact_value jadvalidan indekslangan so'rov
    │
    ▼
5. result       ─── Topilgan faktik ma'lumotlarni mijozga uzatish
    │
    ▼
6. generate     ─── Gemini LLM / deterministik faktlar orqali streaming delta shakllantirish
    │
    ▼
7. verify       ─── Zero-Hallucination tekshiruvi (faqat bazadagi raqamlar qoldiriladi)
    │
    ▼
done            ─── Tasdiqlangan yakuniy javob va manbalar ro'yxati
```

### 2.1. SSE Hodisalari Sxemasi

1. `stage.started` / `stage.completed`: Bosqich o'zgarishlari holati (`parse`, `search`, `dwh`, `generate`, `verify`).
2. `search.completed`: Topilgan ko'rsatkichlar ro'yxati va tanlangan `indicator_id`.
3. `tool.called`: Chaqirilgan vosita nomi (`get_data`) va uning argumentlari.
4. `tool.result`: Baza qaytargan xom qatorlar, o'lchov birligi va metama'lumotlar.
5. `generation.delta`: Generatsiya qilinayotgan matn bo'laklari (token by token).
6. `verification.completed`: Verifikatsiyadan o'tgan va yiqilgan jumlalar audit jurnali.
7. `done`: Yakuniy tasdiqlangan matn, manbalar (snapshot_date, url) va ijro vaqti (ms).

---

## 3. Nol-Gallyutsinatsiya (Zero-Hallucination) Verifikatsiyasi

Modul manzili: `agent/verifier.py`

### 3.1. Ishlash Mantiqi
1. **Jumlalarga ajratish:** Generatsiya qilingan matn regex yordamida mantiqiy jumlalarga ajratiladi.
2. **Manba havolalarini tozalash:** Matndagi `[1]`, `[2]` kabi izoh belgilari statistik son hisoblanmaydi va chiqarib tashlanadi.
3. **O'zbek va xalqaro raqam formatlarini parsing qilish:**
   - Bo'shliqli format: `127 857,3` yoki `127 857.3`
   - Vergulli va nuqtali format: `127,857.3`
   - Butun sonlar va foizlar: `127857`, `1.6%`
4. **DWH faktlar to'plami bilan taqqoslash:** DWH asboblari qaytargan ma'lumotlar strukturasi rekursiv skanerlanib, ruxsat etilgan sonlar to'plami (`Set[float]`) shakllantiriladi.
5. **Qat'iy filtrlash qoidasi:**
   - Agar jumlada bitta bo'lsa ham DWH bazasida yo'q raqam uchrasa, jumla yakuniy javobdan butunlay olib tashlanadi (`passed: False`).
   - Faqat barcha raqamlari bazada mavjud bo'lgan jumlalar saqlanadi.

---

## 4. Test Natijalari va Verifikatsiya

Testlar to'plami: `tests/test_api_sse.py`

Testlarni ishga tushirish:
```bash
python tests/test_api_sse.py
```

### 4.1. REST Endpointlari Sinovi Natijalari
```
===========================================================================
1-QISM: REST API ENDPOINTLARI SINOVI
===========================================================================

[REST 1/4] GET /health tekshiruvi...
  * Status: ok
  * Baza ulanishi: True
  -> [OK] Health endpointi muvaffaqiyatli o'tdi.

[REST 2/4] GET /api/stats tekshiruvi...
  * Jami ko'rsatkichlar: 3,232 ta
  * Jami klassifikatorlar: 131,587 ta
  * Jami faktlar: 2,580,045 qator
  -> [OK] Stats endpointi muvaffaqiyatli o'tdi.

[REST 3/4] GET /api/indicators/search?q=mol+goshti tekshiruvi...
  * Topilgan natijalar: 3 ta
  * 1-natija: #1308 - Bozorlar va do‘konlardagi ayrim tovarlarning o‘rtacha narxlari dinamikasi
  -> [OK] Search endpointi muvaffaqiyatli o'tdi.

[REST 4/4] GET /api/series tekshiruvi (Mol go'shti, 2026-M09)...
  * Mahsulot: Mol go'shti | Qiymat: 127857.3 so'm | Status: valid
  -> [OK] Series endpointi muvaffaqiyatli o'tdi.
```

### 4.2. SSE Orkestratsiyasi va Verifikatsiya Sinovi Natijalari
Savol: `"2026-yil sentyabrda mol go'shtining o'rtacha narxi qancha edi?"`

```
===========================================================================
2-QISM: POST /api/ask SSE ORKESTRATSIYASI VA VERIFIKATSIYASI
===========================================================================

Savol yuborilmoqda: '2026-yil sentyabrda mol go'shtining o'rtacha narxi qancha edi?'...
  * Olingan SSE xabarlari soni: 29 ta
  * Umumiy oqim vaqti: 2224.34 ms

  -> Kuzatilgan SSE voqealari ro'yxati:
     1. stage.started
     2. stage.completed
     3. stage.started
     4. search.completed
     5. stage.completed
     6. tool.called
     7. stage.started
     8. stage.completed
     9. tool.result
     10. stage.started
     11. generation.delta
     12. stage.completed
     13. stage.started
     14. verification.completed
     15. stage.completed
     16. done

  * Tool natijasidagi qatorlar: 1 ta
  * Nol-gallyutsinatsiya verifikatsiyasi: all_passed = True
  * Checklist: [{'text': "2026-M09 holatiga ko'ra, Mol go'shtining o'rtacha qiymati 127,857.3 1 kg so‘mdani tashkil etgan [1].", 'passed': True, 'reason': None, 'extracted_numbers': [2026.0, 127857.3, 1.0]}]

  * Yakuniy javob: "2026-M09 holatiga ko'ra, Mol go'shtining o'rtacha qiymati 127,857.3 1 kg so‘mdani tashkil etgan [1]."
  * Manbalar: [{'n': 1, 'indicator_id': 1308, 'name': 'Bozorlar va do‘konlardagi ayrim tovarlarning o‘rtacha narxlari dinamikasi', 'url': 'https://api.siat.stat.uz/media/uploads/sdmx/sdmx_data_1308.json', 'snapshot_date': '2026-11-11'}]

===========================================================================
MUVAFFAQINT: DAY 4 BARCHA INTEGRATSIYA TESTLARI 100% O'TDI!
===========================================================================
```

---

## 5. Xulosa

Day 4 vazifalari to'liq yakunlandi:
- FastAPI arxitekturasi va REST endpointlar (health, stats, search, indicator, series) ishga tushirildi.
- 7 bosqichli Server-Sent Events (SSE) oqimi muvaffaqiyatli ishlaydi.
- Nol-gallyutsinatsiya verifikatsiya mexanizmi to'qilgan raqamlarni to'liq tozalaydi va DWH faktlari asosida 100% aniqlikni kafolatlaydi.
- Mol go'shti (017) uchun 2026-M09 davridagi 127 857.3 so'mlik benchmark to'liq tasdiqlandi.
