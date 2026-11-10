-- =============================================================================
-- SIAT STAT DWH: Asosiy Ma'lumotlar Bazasi Sxemasi (schema.sql)
-- Loyiha: siat.stat.uz MCP Loyihasi
-- Muallif: Siddiq (Backend & Database Lead)
-- Sxemalar: raw -> staging -> dwh -> mart
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Sxemalarni yaratish
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS dwh;
CREATE SCHEMA IF NOT EXISTS mart;

-- -----------------------------------------------------------------------------
-- 2. Kengaytmalar (Extensions)
-- -----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- -----------------------------------------------------------------------------
-- 3. Yordamchi funksiyalar (Helper Functions)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION dwh.normalize_text(input_text TEXT)
RETURNS TEXT AS $$
BEGIN
    IF input_text IS NULL THEN
        RETURN '';
    END IF;
    input_text := REPLACE(input_text, 'oʻ', 'o''');
    input_text := REPLACE(input_text, 'o‘', 'o''');
    input_text := REPLACE(input_text, 'o’', 'o''');
    input_text := REPLACE(input_text, 'o`', 'o''');
    input_text := REPLACE(input_text, 'gʻ', 'g''');
    input_text := REPLACE(input_text, 'g‘', 'g''');
    input_text := REPLACE(input_text, 'g’', 'g''');
    input_text := REPLACE(input_text, 'g`', 'g''');
    RETURN LOWER(TRIM(input_text));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- -----------------------------------------------------------------------------
-- 4. O'lchov (Dimension) Jadvallari
-- -----------------------------------------------------------------------------

-- 4.1. dim_indicator: Statistik ko'rsatkichlar
CREATE TABLE IF NOT EXISTS dwh.dim_indicator (
    indicator_id INTEGER PRIMARY KEY,           -- SIAT ID (masalan: 1308)
    code VARCHAR(50),                           -- Rasmiy kod (masalan: '1.11.03.0001')
    name_uz TEXT NOT NULL,
    name_ru TEXT,
    name_en TEXT,
    name_uzc TEXT,
    unit_uz VARCHAR(100),
    unit_ru VARCHAR(100),
    unit_en VARCHAR(100),
    unit_uzc VARCHAR(100),
    periodicity VARCHAR(50),
    organization TEXT,
    methodology TEXT,
    notes TEXT,
    last_modified_date DATE,
    source_url TEXT,
    is_cumulative BOOLEAN DEFAULT FALSE,
    search_vector tsvector,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4.2. dim_item: Qatorlar/klassifikatorlar (mahsulot, hudud...)
-- QAT'IY QOIDA: item_code matn (VARCHAR/TEXT) bo'lishi shart!
CREATE TABLE IF NOT EXISTS dwh.dim_item (
    item_id SERIAL PRIMARY KEY,
    indicator_id INTEGER NOT NULL REFERENCES dwh.dim_indicator(indicator_id) ON DELETE CASCADE,
    item_code VARCHAR(100) NOT NULL,
    name_uz TEXT NOT NULL,
    name_ru TEXT,
    name_en TEXT,
    name_uzc TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_indicator_item_code UNIQUE (indicator_id, item_code)
);

-- 4.3. dim_period: Vaqt davrlari
CREATE TABLE IF NOT EXISTS dwh.dim_period (
    period_key VARCHAR(20) PRIMARY KEY,         -- '2026-M09', '2026-Q3', '2026'
    year INTEGER NOT NULL,
    quarter INTEGER,
    month INTEGER,
    period_type VARCHAR(20) NOT NULL,           -- 'monthly', 'quarterly', 'yearly', 'cumulative'
    start_date DATE,
    end_date DATE
);

-- -----------------------------------------------------------------------------
-- 5. Fakt (Fact) Jadvali
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dwh.fact_value (
    fact_id BIGSERIAL PRIMARY KEY,
    indicator_id INTEGER NOT NULL REFERENCES dwh.dim_indicator(indicator_id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES dwh.dim_item(item_id) ON DELETE CASCADE,
    period_key VARCHAR(20) NOT NULL REFERENCES dwh.dim_period(period_key),
    value NUMERIC(20, 4),
    raw_value TEXT,
    status VARCHAR(30) DEFAULT 'valid',         -- 'valid', 'zero_marked', 'missing', 'calculated'
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fact_indicator_item_period_snapshot UNIQUE (indicator_id, item_id, period_key, snapshot_date)
);

-- -----------------------------------------------------------------------------
-- 6. Triggerlar (Triggers)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION dwh.update_indicator_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('simple', COALESCE(dwh.normalize_text(NEW.name_uz), '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(dwh.normalize_text(NEW.name_ru), '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(dwh.normalize_text(NEW.name_en), '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(NEW.code, '')), 'A');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_indicator_search_vector ON dwh.dim_indicator;
CREATE TRIGGER trg_indicator_search_vector
BEFORE INSERT OR UPDATE ON dwh.dim_indicator
FOR EACH ROW
EXECUTE FUNCTION dwh.update_indicator_search_vector();

-- -----------------------------------------------------------------------------
-- 7. Indekslar (Indexes)
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_dim_item_indicator ON dwh.dim_item(indicator_id);
CREATE INDEX IF NOT EXISTS idx_dim_period_year ON dwh.dim_period(year);

CREATE INDEX IF NOT EXISTS idx_fact_indicator_period ON dwh.fact_value(indicator_id, period_key);
CREATE INDEX IF NOT EXISTS idx_fact_item_period ON dwh.fact_value(item_id, period_key);
CREATE INDEX IF NOT EXISTS idx_fact_snapshot ON dwh.fact_value(snapshot_date);

-- Qidiruv indekslari (tsvector va pg_trgm GIN)
CREATE INDEX IF NOT EXISTS idx_dim_indicator_fts ON dwh.dim_indicator USING gin (search_vector);
CREATE INDEX IF NOT EXISTS idx_dim_indicator_name_uz_trgm ON dwh.dim_indicator USING gin (dwh.normalize_text(name_uz) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_dim_indicator_name_ru_trgm ON dwh.dim_indicator USING gin (LOWER(name_ru) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_dim_item_name_uz_trgm ON dwh.dim_item USING gin (dwh.normalize_text(name_uz) gin_trgm_ops);
