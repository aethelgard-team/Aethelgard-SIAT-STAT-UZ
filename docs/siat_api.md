# SIAT API Hujjatlari (docs/siat_api.md)

Ushbu hujjatda `siat.stat.uz` (O'zbekiston Respublikasi Prezidenti huzuridagi Statistika agentligining integrallashgan axborot tizimi) ochiq API endpointlari va ma'lumot tuzilmalari qayd etilgan.

## Asosiy URL
- **VUE_APP_API_URL**: `https://api.siat.stat.uz/`
- **Frontend SPA**: `https://siat.stat.uz/`

---

## 1. Asosiy API Endpointlar

### 1.1. Barcha ko'rsatkichlar katalogi (Tugallovchi qatlam - Last Layer)
- **URL**: `https://api.siat.stat.uz/sdmx/last-layer/?page={page}`
- **Usul**: `GET`
- **Jami ko'rsatkichlar**: **3 239 ta**
- **Sahifalash (Pagination)**: Bir sahifada 100 tadan (jami ~33 ta sahifa)
- **Har bir element tuzilishi**:
  ```json
  {
    "id": 2943,
    "name": "Qishloq, o‘rmon va baliqchilik xo‘jaligi mahsulot (xizmat)larining umumiy hajmi (choraklik)",
    "name_uz": "...",
    "name_en": "...",
    "name_ru": "...",
    "name_uzc": "...",
    "classifier": 1
  }
  ```

### 1.2. Yuqori toifalar (Kategoriyalar daraxti)
- **URL**: `https://api.siat.stat.uz/sdmx/` yoki `https://api.siat.stat.uz/sdmx/json/`
- **Usul**: `GET`
- **Tavsif**: Asosiy yo'nalishlar (Iqtisodiy, Demografiya va mehnat, Ijtimoiy statistika va h.k.)

### 1.3. Bolalar toifalari (Children)
- **URL**: `https://api.siat.stat.uz/sdmx/{id}/children/`
- **Usul**: `GET`

### 1.4. Ko'rsatkich haqida to'liq ma'lumot
- **URL**: `https://api.siat.stat.uz/sdmx/{id}/`
- **Usul**: `GET`

### 1.5. Ko'rsatkich metama'lumotlari
- **URL**: `https://api.siat.stat.uz/sdmx/{id}/metadata/`
- **Usul**: `GET`
- **Qaytaradi**: Birinchi chop etilgan sana, so'nggi yangilanish, o'lchov birligi, mas'ul boshqarma.

---

## 2. SDMX Ma'lumotlar to'plami (Data Downloads)

Har bir ko'rsatkichning to'liq faktik ma'lumotlari statik JSON fayl sifatida saqlangan:
- **Yuklab olish URL**: `https://api.siat.stat.uz/media/uploads/sdmx/sdmx_data_{id}.json`
- **Misol**: `https://api.siat.stat.uz/media/uploads/sdmx/sdmx_data_1308.json` (Bozorlardagi narxlar dinamikasi)
- **Fayl tuzilishi**:
  - `metadata`: Ko'rsatkich kodi (masalan, `1.11.03.0001`), nomi, davriyligi (oylik/choraklik/yillik), metodika, 4 tilda.
  - `data`: Klassifikatorlar (`Code`, `Klassifikator`, `Klassifikator_ru`, `Klassifikator_en`) va davrlar bo'yicha ustunlar (`2021-M01`, `2026-M09` va h.k.).

---

## 3. Yuklab olish qoidalari (Rate Limit & Retry)
1. **Tezlik**: Sekundiga ko'pi bilan 1–2 ta so'rov.
2. **Timeout**: 30 soniya.
3. **Qayta urinish**: Aloqa uzilsa yoki xatolik bersa 3 marta (`tenacity` orqali).
4. **Natija fiksatsiyasi**: Har bir yuklangan fayl `manifest.csv` ga (`id`, `status_code`, `file_size_bytes`, `sha256`) yoziladi.
