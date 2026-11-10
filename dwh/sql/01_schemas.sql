-- =============================================================================
-- 01_schemas.sql: DWH Loyihasi uchun sxemalar (Schemas)
-- Arxitektura: raw -> staging -> dwh -> mart
-- =============================================================================

-- 1. raw: SIAT dan kelgan xom JSON fayllar o'zgarishsiz saqlanadi
CREATE SCHEMA IF NOT EXISTS raw;

-- 2. staging: tozalangan, lekin hali birlashtirilmagan oraliq ma'lumotlar
CREATE SCHEMA IF NOT EXISTS staging;

-- 3. dwh: asosiy tahliliy ombor (yulduz sxema: fact va dimension jadvallar)
CREATE SCHEMA IF NOT EXISTS dwh;

-- 4. mart: biznes/yakuniy tahlil uchun tayyor tezkor ko'rinishlar (views / materialised views)
CREATE SCHEMA IF NOT EXISTS mart;
