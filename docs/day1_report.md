# Day 1: Xom ma'lumotlar integratsiyasi va sifat auditi

Barcha buyruqlar loyiha ildizida bajariladi:

## 1. Ma'lumotlarni yig'ish (Ingestion)

Katalog va SDMX JSON fayllarni yuklash:
```bash
python -m etl.fetch_catalog     # SIAT katalogini yuklash -> data/raw/catalog.json
python -m etl.download_raw      # 3 239 ta datasetni parallel yuklash
```

Yuklash natijalari:
- Jami katalog ko'rsatkichlari: 3 239 ta
- Muvaffaqiyatli saqlangan fayllar: 3 232 ta (99.78% qamrov)
- Server xatosi (404 Not Found): 7 ta (stat.uz tomonida o'chirilgan resurslar)
- Buzilgan yoki bo'sh JSON fayllar: 0 ta
- Saqlash manzili: data/raw/2026-11-11/sdmx_data_<id>.json

## 2. Sifat auditi va ma'lumotlar anomaliyalari

Sifat tekshiruvini ishga tushirish:
```bash
python -m etl.audit_quality --input-dir data/raw/2026-11-11
```

Aniqlangan anomaliyalar va qarorlar:
- Kirillcha 'М' harfi:
  Sanalarda 215 876 ta holatda lotin 'M' o'rniga kirill 'М' ishlatilgan (masalan, 2021-М01).
  Yechim: `period_key.replace('М', 'M').replace('м', 'M').strip()` orqali lotinchaga normallashtiriladi.
- 0.0 qiymatlar (Zero-fill anomaliyasi):
  Jami 284 366 ta qatorda 0.0 qiymat qayd etilgan (mavsumiylik yoki yetishmayotgan ma'lumot).
  Yechim: O'rtacha hisoblash agregatsiyalarini buzmasligi uchun `value = NULL`, xom holat `raw_value = '0.0'` va `status = 'zero_marked'` qilib ajratiladi.
- Davr turlari taqsimoti:
  - Yillik (YYYY): 1 310 852 qator
  - Oylik (YYYY-Mnn): 1 087 081 qator
  - Choraklik (YYYY-Qn): 165 669 qator
  - Boshqa maxsus davrlar: ~5 000 qator
- Kodlar yaxlitligi:
  Hudud va tarmoq kodlarida bosh nollar mavjud (017, 001).
  Yechim: Integer turiga o'tkazilmaydi, qat'iy ravishda VARCHAR turida saqlanadi.
