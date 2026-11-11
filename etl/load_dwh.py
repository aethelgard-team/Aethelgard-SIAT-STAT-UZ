"""
=============================================================================
SIAT STAT DWH: ETL Ingestion Pipeline (load_dwh.py)
Loyiha: siat.stat.uz MCP Loyihasi
Muallif: Siddiq (Backend & Database Lead)
Tavsif:
  data/raw/<sana>/ papkasidagi 3 232 ta SDMX JSON fayllarni o'qib,
  anomaliyalarni tozalab (Kirillcha 'М', 0.0 qiymatlar, matnli kodlar),
  PostgreSQL DWH (dim_indicator, dim_item, dim_period, fact_value)
  jadvallariga execute_values orqali to'plamlab (batch) yuklaydi.
=============================================================================
"""

import os
import sys
import json
import re
import time
import argparse
import calendar
from datetime import datetime, date
from typing import Dict, List, Tuple, Any, Optional

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# .env faylidan sozlamalarni yuklash
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
DB_NAME = os.getenv("DB_NAME", "siat_dwh")

# O'zgarmas maydonlar (klassifikator va metadata qatorlarida davr bo'lmagan kalitlar)
NON_PERIOD_KEYS = {
    "Code", "csa_code", "id", 
    "Klassifikator", "Klassifikator_ru", "Klassifikator_en", "Klassifikator_uzc"
}

# -----------------------------------------------------------------------------
# 1. Baza bilan bog'lanish yordamchisi
# -----------------------------------------------------------------------------
def get_db_connection():
    """PostgreSQL bazasiga ulanish obyekti qaytaradi."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME,
        connect_timeout=10
    )


# -----------------------------------------------------------------------------
# 2. Katalog ma'lumotlarini yuklash (Fallback uchun)
# -----------------------------------------------------------------------------
def load_catalog_map(catalog_path: str = "data/catalog.json") -> Dict[int, dict]:
    """Katalogdagi ko'rsatkichlar nomlarini ID bo'yicha xaritaga oladi."""
    if not os.path.exists(catalog_path):
        return {}
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            inds = data.get("indicators", [])
            return {int(item["id"]): item for item in inds if "id" in item}
    except Exception as e:
        print(f"[!] Katalog yuklashda ogohlantirish: {e}")
        return {}


# -----------------------------------------------------------------------------
# 3. Davr parseri va normalizatori (Kirill 'М' -> Lotin 'M')
# -----------------------------------------------------------------------------
def parse_and_normalize_period(raw_key: str) -> Optional[Tuple[str, int, Optional[int], Optional[int], str, Optional[date], Optional[date]]]:
    """
    Davr kalitini tozalaydi, normalizatsiya qiladi va dim_period qatorini qaytaradi.
    Qaytaradi: (period_key, year, quarter, month, period_type, start_date, end_date)
    
    QOIDALAR:
    - Kirillcha 'М' va 'м' harflari lotincha 'M' ga o'tkaziladi.
    - 'Unnamed:' kabi yaroqsiz ustunlar bekor qilinadi.
    - Uzunligi 20 belgidan oshmaydigan qat'iy format.
    """
    if not raw_key or not isinstance(raw_key, str):
        return None

    # 1. Tozalash va Kirill 'М' harfini lotinga o'tkazish
    cleaned = raw_key.replace("М", "M").replace("м", "M").strip()
    
    # Yaroqsiz pandas/excel chiqindilarini tashlab yuborish
    if cleaned.startswith("Unnamed:") or len(cleaned) > 20 or not cleaned:
        return None

    # A. Oylik davr: YYYY-Mnn yoki YYYY-Mn (Masalan: 2026-M09, 2024-M1, 2021-М01)
    m = re.match(r"^(\d{4})-[mM](\d{1,2})$", cleaned)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        if 1 <= month <= 12:
            quarter = (month - 1) // 3 + 1
            norm_key = f"{year}-M{month:02d}"
            try:
                start_date = date(year, month, 1)
                last_day = calendar.monthrange(year, month)[1]
                end_date = date(year, month, last_day)
            except (ValueError, OverflowError):
                start_date, end_date = None, None
            return (norm_key, year, quarter, month, "monthly", start_date, end_date)

    # B. Choraklik davr chiziqcha bilan: YYYY-Qn (Masalan: 2026-Q3, 2024-q1)
    m = re.match(r"^(\d{4})-[qQ](\d)$", cleaned)
    if m:
        year = int(m.group(1))
        quarter = int(m.group(2))
        if 1 <= quarter <= 4:
            norm_key = f"{year}-Q{quarter}"
            try:
                start_month = (quarter - 1) * 3 + 1
                end_month = quarter * 3
                start_date = date(year, start_month, 1)
                last_day = calendar.monthrange(year, end_month)[1]
                end_date = date(year, end_month, last_day)
            except (ValueError, OverflowError):
                start_date, end_date = None, None
            return (norm_key, year, quarter, None, "quarterly", start_date, end_date)

    # C. Choraklik davr chiziqchasiz: YYYYQn (Masalan: 2021Q3)
    m = re.match(r"^(\d{4})[qQ](\d)$", cleaned)
    if m:
        year = int(m.group(1))
        quarter = int(m.group(2))
        if 1 <= quarter <= 4:
            norm_key = f"{year}-Q{quarter}"
            try:
                start_month = (quarter - 1) * 3 + 1
                end_month = quarter * 3
                start_date = date(year, start_month, 1)
                last_day = calendar.monthrange(year, end_month)[1]
                end_date = date(year, end_month, last_day)
            except (ValueError, OverflowError):
                start_date, end_date = None, None
            return (norm_key, year, quarter, None, "quarterly", start_date, end_date)

    # D. Yillik davr: YYYY (Masalan: 2026, 2019)
    m = re.match(r"^(\d{4})$", cleaned)
    if m:
        year = int(m.group(1))
        try:
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
        except (ValueError, OverflowError):
            start_date, end_date = None, None
        return (cleaned, year, None, None, "yearly", start_date, end_date)

    # E. Akademik / O'quv yili: YYYY/YYYY (Masalan: 2021/2022)
    m = re.match(r"^(\d{4})/(\d{4})$", cleaned)
    if m:
        year = int(m.group(1))
        year2 = int(m.group(2))
        try:
            start_date = date(year, 9, 1)
            end_date = date(year2, 6, 30)
        except (ValueError, OverflowError):
            start_date, end_date = None, None
        return (cleaned, year, None, None, "academic_year", start_date, end_date)

    # F. Yarim yillik davr: YYYY-Hn (Masalan: 2026-H1)
    m = re.match(r"^(\d{4})-[hH](\d)$", cleaned)
    if m:
        year = int(m.group(1))
        h = int(m.group(2))
        try:
            start_date = date(year, 1, 1) if h == 1 else date(year, 7, 1)
            end_date = date(year, 6, 30) if h == 1 else date(year, 12, 31)
        except (ValueError, OverflowError):
            start_date, end_date = None, None
        return (f"{year}-H{h}", year, h * 2, None, "half_yearly", start_date, end_date)

    # G. Boshqa formatlar (Ichida 4 xonali yil bo'lgan har qanday qisqa kalit)
    m = re.search(r"\d{4}", cleaned)
    if m:
        year = int(m.group(0))
        norm_key = cleaned[:20]
        try:
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
        except (ValueError, OverflowError):
            start_date, end_date = None, None
        return (norm_key, year, None, None, "other", start_date, end_date)

    return None


# -----------------------------------------------------------------------------
# 4. Qiymat tozalovchi (0.0 Anomaliyasini boshqarish)
# -----------------------------------------------------------------------------
def clean_fact_value(raw_val: Any) -> Tuple[Optional[float], Optional[str], str]:
    """
    Xom qiymatni tozalaydi va holatini aniqlaydi.
    Qaytaradi: (value: float | None, raw_value: str, status: str)
    
    QIZIL QOIDA:
    0.0 va 0 bo'lgan qiymatlar tahliliy hisob-kitobni buzmasligi uchun:
    value = None, raw_value = '0.0', status = 'zero_marked' bo'ladi!
    """
    if raw_val is None:
        return (None, None, "missing")

    val_str = str(raw_val).strip()

    # Bo'sh matnlar yoki maxsus belgilar
    if not val_str or val_str.lower() in ("none", "null", "nan", "-", "—", "yo'q", "yo‘q"):
        return (None, val_str if val_str else None, "missing")

    # To'g'ridan-to'g'ri nol tekshiruvi
    if raw_val == 0 or raw_val == 0.0 or val_str in ("0", "0.0", "0,0", ".0", "0."):
        return (None, val_str, "zero_marked")

    # Sonli formatga keltirish (bo'shliq va vergulni tuzatish)
    cleaned_num = val_str.replace(" ", "").replace(",", ".")
    try:
        num = float(cleaned_num)
        if num == 0.0:
            return (None, val_str, "zero_marked")
        return (num, val_str, "valid")
    except (ValueError, TypeError):
        # Matnli yoki noaniq qiymat bo'lsa
        return (None, val_str, "missing")


# -----------------------------------------------------------------------------
# 5. Metadata ajratuvchi (dim_indicator uchun)
# -----------------------------------------------------------------------------
def extract_indicator_metadata(meta_list: list, indicator_id: int, catalog_item: Optional[dict]) -> dict:
    """JSON metadata massividan dim_indicator ustunlarini yig'adi."""
    meta_dict = {}
    last_mod_dates = []

    for m in meta_list:
        if not isinstance(m, dict):
            continue
        n_uz = (m.get("name_uz") or m.get("name_ru") or m.get("name") or "").lower().strip()
        n_norm = re.sub(r"['`’‘ʻ]", "'", n_uz)

        # "So'nggi o'zgartirilgan sana" bir necha marta kelsa, eng yangisini olamiz
        if "o'zgartirilgan sana" in n_norm or "последнего изменения" in n_norm or "last modified" in n_norm:
            d_val = (m.get("value_uz") or m.get("value_ru") or m.get("value") or "").strip()
            date_match = re.search(r"\d{4}-\d{2}-\d{2}", d_val)
            if date_match:
                try:
                    last_mod_dates.append(datetime.strptime(date_match.group(0), "%Y-%m-%d").date())
                except ValueError:
                    pass

        if n_norm not in meta_dict:
            meta_dict[n_norm] = m

    def get_val(patterns: List[str], lang: str = "uz") -> Optional[str]:
        for pat in patterns:
            for k, m in meta_dict.items():
                if pat in k:
                    val = m.get(f"value_{lang}") or m.get("value")
                    if val is not None and str(val).strip():
                        return str(val).strip()
        return None

    # Rasmiy kod
    code = get_val(["identifikatsiya", "код", "identification"])

    # Nomlar (agar metadata'da bo'lmasa catalog.json fallback qo'llanadi)
    name_uz = (
        get_val(["nomi", "имя", "name"], "uz")
        or (catalog_item.get("name_uz") if catalog_item else None)
        or (catalog_item.get("name") if catalog_item else None)
        or f"Ko'rsatkich #{indicator_id}"
    )
    name_ru = get_val(["nomi", "имя", "name"], "ru") or (catalog_item.get("name_ru") if catalog_item else None)
    name_en = get_val(["nomi", "имя", "name"], "en") or (catalog_item.get("name_en") if catalog_item else None)
    name_uzc = get_val(["nomi", "имя", "name"], "uzc") or (catalog_item.get("name_uzc") if catalog_item else None)

    # O'lchov birligi
    unit_uz = get_val(["birligi", "единица", "unit"], "uz")
    unit_ru = get_val(["birligi", "единица", "unit"], "ru")
    unit_en = get_val(["birligi", "единица", "unit"], "en")
    unit_uzc = get_val(["birligi", "единица", "unit"], "uzc")

    # Davriyligi, Tashkilot, Metodika, Izoh
    periodicity = get_val(["davriyligi", "периодичность", "periodicity"], "uz")
    organization = get_val(["boshqarma", "tayyorlovchi", "управление", "составитель", "department"], "uz")
    methodology = get_val(["metodikasi", "методология", "методы", "methodology"], "uz")
    notes = get_val(["izoh", "примечание", "note"], "uz")

    # Eng yangi sana
    last_modified_date = max(last_mod_dates) if last_mod_dates else None

    # Manba URL
    source_url = f"https://api.siat.stat.uz/media/uploads/sdmx/sdmx_data_{indicator_id}.json"

    # Jamlanma (cumulative) belgisi
    is_cum = False
    full_info = f"{name_uz} {periodicity} {notes}".lower()
    if "jamlanma" in full_info or "нарастающ" in full_info or "cumulative" in full_info:
        is_cum = True

    return {
        "indicator_id": indicator_id,
        "code": code,
        "name_uz": name_uz,
        "name_ru": name_ru,
        "name_en": name_en,
        "name_uzc": name_uzc,
        "unit_uz": unit_uz,
        "unit_ru": unit_ru,
        "unit_en": unit_en,
        "unit_uzc": unit_uzc,
        "periodicity": periodicity,
        "organization": organization,
        "methodology": methodology,
        "notes": notes,
        "last_modified_date": last_modified_date,
        "source_url": source_url,
        "is_cumulative": is_cum,
    }


# -----------------------------------------------------------------------------
# 6. Bitta Datasetni qayta ishlash funksiyasi
# -----------------------------------------------------------------------------
def process_single_dataset(file_path: str, snapshot_date: date, catalog_map: Dict[int, dict]) -> Optional[dict]:
    """Bitta JSON faylni o'qib, DWH modellariga tayyorlangan to'plamlarni qaytaradi."""
    filename = os.path.basename(file_path)
    id_match = re.search(r"sdmx_data_(\d+)\.json", filename)
    if not id_match:
        return None
    indicator_id = int(id_match.group(1))

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
    except Exception as e:
        print(f"[XATO] {filename} faylini o'qib bo'lmadi: {e}")
        return None

    if not content or not isinstance(content, list) or len(content) == 0:
        return None

    dataset = content[0]
    meta_list = dataset.get("metadata", [])
    data_rows = dataset.get("data", [])

    # 1. Indicator
    catalog_item = catalog_map.get(indicator_id)
    indicator_record = extract_indicator_metadata(meta_list, indicator_id, catalog_item)

    # 2. Items va Periods hamda Facts
    items_records = []
    periods_records = {}
    facts_records = []

    seen_item_codes = set()
    cyrillic_m_count = 0
    zero_marked_count = 0

    for idx, row in enumerate(data_rows):
        if not isinstance(row, dict):
            continue

        # QIZIL QOIDA: item_code matn (str) bo'lishi shart! Masalan "017"
        raw_code = row.get("Code") or row.get("csa_code") or f"{idx + 1}"
        item_code = str(raw_code).strip()
        if not item_code:
            item_code = f"ROW_{idx + 1}"

        if item_code not in seen_item_codes:
            seen_item_codes.add(item_code)
            name_uz = str(row.get("Klassifikator") or f"Item {item_code}").strip()
            name_ru = row.get("Klassifikator_ru")
            name_en = row.get("Klassifikator_en")
            name_uzc = row.get("Klassifikator_uzc")
            items_records.append((
                indicator_id,
                item_code,
                name_uz,
                name_ru,
                name_en,
                name_uzc
            ))

        # Ustunlarni (davrlarni) aylanib chiqish (Wide -> Long)
        for col_key, raw_val in row.items():
            if col_key in NON_PERIOD_KEYS:
                continue

            if "М" in col_key or "м" in col_key:
                cyrillic_m_count += 1

            parsed_period = parse_and_normalize_period(col_key)
            if not parsed_period:
                continue

            period_key, year, quarter, month, p_type, s_date, e_date = parsed_period
            if period_key not in periods_records:
                periods_records[period_key] = (period_key, year, quarter, month, p_type, s_date, e_date)

            # QIZIL QOIDA: 0.0 anomaliyasini tozalash
            val_clean, raw_val_str, status = clean_fact_value(raw_val)
            if status == "zero_marked":
                zero_marked_count += 1

            facts_records.append({
                "indicator_id": indicator_id,
                "item_code": item_code,
                "period_key": period_key,
                "value": val_clean,
                "raw_value": raw_val_str,
                "status": status,
                "snapshot_date": snapshot_date
            })

    return {
        "indicator": indicator_record,
        "items": items_records,
        "periods": list(periods_records.values()),
        "facts": facts_records,
        "cyrillic_m_count": cyrillic_m_count,
        "zero_marked_count": zero_marked_count
    }


# -----------------------------------------------------------------------------
# 7. DWH ga to'plamli yozish (Batch Ingestion)
# -----------------------------------------------------------------------------
def load_datasets_to_dwh(datasets_data: List[dict], conn) -> Tuple[int, int, int, int]:
    """
    To'plangan datasetlarni tranzaksiya ichida execute_values orqali quyadi.
    Qaytaradi: (indicators_count, items_count, periods_count, facts_count)
    """
    cursor = conn.cursor()

    # 1. dim_indicator upsert
    indicators_tuples = []
    for d in datasets_data:
        ind = d["indicator"]
        indicators_tuples.append((
            ind["indicator_id"], ind["code"], ind["name_uz"], ind["name_ru"],
            ind["name_en"], ind["name_uzc"], ind["unit_uz"], ind["unit_ru"],
            ind["unit_en"], ind["unit_uzc"], ind["periodicity"], ind["organization"],
            ind["methodology"], ind["notes"], ind["last_modified_date"],
            ind["source_url"], ind["is_cumulative"]
        ))

    indicator_sql = """
        INSERT INTO dwh.dim_indicator (
            indicator_id, code, name_uz, name_ru, name_en, name_uzc,
            unit_uz, unit_ru, unit_en, unit_uzc, periodicity, organization,
            methodology, notes, last_modified_date, source_url, is_cumulative
        ) VALUES %s
        ON CONFLICT (indicator_id) DO UPDATE SET
            code = EXCLUDED.code,
            name_uz = EXCLUDED.name_uz,
            name_ru = EXCLUDED.name_ru,
            name_en = EXCLUDED.name_en,
            name_uzc = EXCLUDED.name_uzc,
            unit_uz = EXCLUDED.unit_uz,
            unit_ru = EXCLUDED.unit_ru,
            unit_en = EXCLUDED.unit_en,
            unit_uzc = EXCLUDED.unit_uzc,
            periodicity = EXCLUDED.periodicity,
            organization = EXCLUDED.organization,
            methodology = EXCLUDED.methodology,
            notes = EXCLUDED.notes,
            last_modified_date = EXCLUDED.last_modified_date,
            source_url = EXCLUDED.source_url,
            is_cumulative = EXCLUDED.is_cumulative,
            updated_at = CURRENT_TIMESTAMP;
    """
    if indicators_tuples:
        execute_values(cursor, indicator_sql, indicators_tuples, page_size=100)

    # 2. dim_period upsert
    periods_map = {}
    for d in datasets_data:
        for p in d["periods"]:
            periods_map[p[0]] = p
    periods_tuples = list(periods_map.values())

    period_sql = """
        INSERT INTO dwh.dim_period (
            period_key, year, quarter, month, period_type, start_date, end_date
        ) VALUES %s
        ON CONFLICT (period_key) DO UPDATE SET
            year = EXCLUDED.year,
            quarter = EXCLUDED.quarter,
            month = EXCLUDED.month,
            period_type = EXCLUDED.period_type,
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date;
    """
    if periods_tuples:
        execute_values(cursor, period_sql, periods_tuples, page_size=500)

    # 3. dim_item upsert
    all_items_tuples = []
    indicator_ids = [d["indicator"]["indicator_id"] for d in datasets_data]
    for d in datasets_data:
        all_items_tuples.extend(d["items"])

    item_sql = """
        INSERT INTO dwh.dim_item (
            indicator_id, item_code, name_uz, name_ru, name_en, name_uzc
        ) VALUES %s
        ON CONFLICT (indicator_id, item_code) DO UPDATE SET
            name_uz = EXCLUDED.name_uz,
            name_ru = EXCLUDED.name_ru,
            name_en = EXCLUDED.name_en,
            name_uzc = EXCLUDED.name_uzc;
    """
    if all_items_tuples:
        execute_values(cursor, item_sql, all_items_tuples, page_size=1000)

    # Bazadan yuklangan item_id larni olish (indicator_id, item_code) -> item_id
    cursor.execute("""
        SELECT indicator_id, item_code, item_id 
        FROM dwh.dim_item 
        WHERE indicator_id = ANY(%s);
    """, (indicator_ids,))
    item_id_map = {(row[0], row[1]): row[2] for row in cursor.fetchall()}

    # 4. fact_value upsert
    fact_tuples = []
    for d in datasets_data:
        for f in d["facts"]:
            key = (f["indicator_id"], f["item_code"])
            item_id = item_id_map.get(key)
            if item_id is None:
                continue
            fact_tuples.append((
                f["indicator_id"],
                item_id,
                f["period_key"],
                f["value"],
                f["raw_value"],
                f["status"],
                f["snapshot_date"]
            ))

    fact_sql = """
        INSERT INTO dwh.fact_value (
            indicator_id, item_id, period_key, value, raw_value, status, snapshot_date
        ) VALUES %s
        ON CONFLICT (indicator_id, item_id, period_key, snapshot_date) DO UPDATE SET
            value = EXCLUDED.value,
            raw_value = EXCLUDED.raw_value,
            status = EXCLUDED.status;
    """
    if fact_tuples:
        execute_values(cursor, fact_sql, fact_tuples, page_size=5000)

    conn.commit()
    cursor.close()

    return len(indicators_tuples), len(all_items_tuples), len(periods_tuples), len(fact_tuples)


# -----------------------------------------------------------------------------
# 8. Asosiy Pipeline va CLI
# -----------------------------------------------------------------------------
def run_pipeline(limit: Optional[int] = None, specific_id: Optional[int] = None, batch_size: int = 50):
    """ETL jarayonini boshqaruvchi asosiy funksiya."""
    print("=" * 70)
    print("SIAT DWH ETL PIPELINE: load_dwh.py")
    print(f"Baza: {DB_NAME} | Host: {DB_HOST}:{DB_PORT} | Foydalanuvchi: {DB_USER}")
    print("=" * 70)

    # Snapshot sanasi (Bugungi sana yoki raw papka sanasi)
    raw_base_dir = os.path.join("data", "raw")
    today_str = datetime.now().strftime("%Y-%m-%d")
    raw_date_dir = os.path.join(raw_base_dir, today_str)

    if not os.path.exists(raw_date_dir):
        # Eng yangi sana papkasini topish
        date_folders = [d for d in os.listdir(raw_base_dir) if os.path.isdir(os.path.join(raw_base_dir, d))]
        if date_folders:
            date_folders.sort(reverse=True)
            raw_date_dir = os.path.join(raw_base_dir, date_folders[0])
            today_str = date_folders[0]
        else:
            print(f"[XATO] {raw_base_dir} ichida sana papkasi topilmadi!")
            sys.exit(1)

    try:
        snapshot_date = datetime.strptime(today_str, "%Y-%m-%d").date()
    except ValueError:
        snapshot_date = date.today()

    print(f"[+] Ma'lumotlar papkasi: {raw_date_dir}")
    print(f"[+] Snapshot sanasi: {snapshot_date}")

    # Baza aloqasini tekshirish
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"[XATOLIK] Bazaga ulanib bo'lmadi: {e}")
        sys.exit(1)

    # Katalog nomlarini yuklash
    print("[+] catalog.json yuklanmoqda...")
    catalog_map = load_catalog_map()
    print(f"[OK] Katalogdan {len(catalog_map)} ta ko'rsatkich xaritaga olindi.")

    # Fayllar ro'yxatini shakllantirish
    all_files = [
        os.path.join(raw_date_dir, f)
        for f in os.listdir(raw_date_dir)
        if f.startswith("sdmx_data_") and f.endswith(".json")
    ]
    all_files.sort()
    total_found = len(all_files)
    print(f"[+] Diskda jami {total_found} ta JSON fayl topildi.")

    # Filtrlash
    selected_files = []
    if specific_id is not None:
        target_name = f"sdmx_data_{specific_id}.json"
        selected_files = [f for f in all_files if os.path.basename(f) == target_name]
        if not selected_files:
            print(f"[XATO] sdmx_data_{specific_id}.json fayli topilmadi!")
            sys.exit(1)
        print(f"[!] Test rejimi: Faqat #{specific_id} fayl yuklanadi.")
    elif limit is not None:
        # Test uchun: agar limit berilgan bo'lsa, lekin ichida 1308 bo'lmasa, uni oxiriga qo'shib olamiz
        selected_files = all_files[:limit]
        sample_1308 = [f for f in all_files if "sdmx_data_1308.json" in f]
        if sample_1308 and sample_1308[0] not in selected_files:
            selected_files.append(sample_1308[0])
        print(f"[!] Test rejimi: {len(selected_files)} ta fayl tanlab olindi.")
    else:
        selected_files = all_files
        print(f"[!] To'liq yuklash rejimi: {len(selected_files)} ta fayl yuklanadi.")

    print("-" * 70)

    # Statistika hisoblagichlari
    start_time = time.time()
    total_processed = 0
    total_indicators = 0
    total_items = 0
    total_periods = 0
    total_facts = 0
    total_cyrillic_m = 0
    total_zero_marked = 0

    batch = []

    for idx, fpath in enumerate(selected_files, 1):
        parsed = process_single_dataset(fpath, snapshot_date, catalog_map)
        if parsed:
            batch.append(parsed)
            total_cyrillic_m += parsed["cyrillic_m_count"]
            total_zero_marked += parsed["zero_marked_count"]

        # Batch to'lganda yoki oxirgi faylga yetganda bazaga quyish
        if len(batch) >= batch_size or idx == len(selected_files):
            if batch:
                inds_c, items_c, per_c, facts_c = load_datasets_to_dwh(batch, conn)
                total_indicators += inds_c
                total_items += items_c
                total_facts += facts_c
                total_processed += len(batch)

                elapsed = time.time() - start_time
                pct = (idx / len(selected_files)) * 100
                print(
                    f"[{idx}/{len(selected_files)}] ({pct:5.1f}%) | "
                    f"Faktlar: +{facts_c:,} (Jami: {total_facts:,}) | "
                    f"Vaqt: {elapsed:.1f}s"
                )
                batch = []

    total_time = time.time() - start_time
    print("=" * 70)
    print("YUKLASH MUVAFFAQIYATLI YAKUNLANDI!")
    print(f"  * Qayta ishlangan fayllar: {total_processed} ta")
    print(f"  * Ko'rsatkichlar (dim_indicator): {total_indicators:,} ta")
    print(f"  * Klassifikatorlar (dim_item): {total_items:,} ta")
    print(f"  * Jami faktlar (fact_value): {total_facts:,} ta")
    print(f"  * Tozalangan Kirill 'М' davrlari: {total_cyrillic_m:,} ta")
    print(f"  * Tozalangan 0.0 qiymatlar (zero_marked): {total_zero_marked:,} ta")
    print(f"  * Umumiy sarflangan vaqt: {total_time:.2f} soniya ({total_time / 60:.2f} daqiqa)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # 9. ROADMAP TEKSHIRUVI: Mol go'shti, 2026-M09 (sdmx_data_1308.json)
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("🔍 ROADMAP SINOVI: 'Mol go'shti, 2026-M09' tekshiruvi boshlandi...")
    print("=" * 70)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                i.indicator_id,
                i.name_uz AS indicator_name,
                it.item_code,
                it.name_uz AS item_name,
                f.period_key,
                f.value,
                f.raw_value,
                f.status,
                f.snapshot_date
            FROM dwh.fact_value f
            JOIN dwh.dim_indicator i ON f.indicator_id = i.indicator_id
            JOIN dwh.dim_item it ON f.item_id = it.item_id
            WHERE f.indicator_id = 1308 
              AND it.item_code = '017' 
              AND f.period_key = '2026-M09';
        """)
        row = cur.fetchone()
        if row:
            ind_id, ind_name, item_code, item_name, p_key, val, raw_val, stat, s_date = row
            print(f"[OK] BAZADAN TOPILDI:")
            print(f"  - Ko'rsatkich #{ind_id}: {ind_name}")
            print(f"  - Mahsulot (kod: {item_code}): {item_name}")
            print(f"  - Davr: {p_key}")
            print(f"  - Qiymat: {val:,.1f} so'm (raw: {raw_val}, status: {stat})")
            print(f"  - Snapshot sana: {s_date}")

            expected_val = 127857.3
            if abs(float(val) - expected_val) < 0.01:
                print(f"\n🎯 [MUVAFFAQIYATLI] Bazadagi qiymat ({val}) kutilgan qiymatga ({expected_val}) 100% TENG!")
            else:
                print(f"\n[!] Ogohlantirish: Qiymat kutilgandan farq qildi: {val} != {expected_val}")
        else:
            print("[!] 1308-dataset bazada topilmadi (agar faqat boshqa fayllar tanlangan bo'lsa).")

        cur.close()
    except Exception as e:
        print(f"[XATO] Sinov so'rovida xatolik: {e}")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SIAT DWH ETL Pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Yuklanadigan fayllar sonini cheklash (Test uchun)")
    parser.add_argument("--id", type=int, default=None, help="Bitta aniq ko'rsatkich ID sini yuklash (Masalan: --id 1308)")
    parser.add_argument("--batch-size", type=int, default=50, help="To'plam (batch) hajmi (standart: 50)")
    args = parser.parse_args()

    run_pipeline(limit=args.limit, specific_id=args.id, batch_size=args.batch_size)
