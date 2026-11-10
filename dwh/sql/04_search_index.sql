-- =============================================================================
-- 04_search_index.sql: Vektorsiz tezkor qidiruv (tsvector + pg_trgm GIN)
-- =============================================================================

-- 1. pg_trgm (Trigram) kengaytmasini yoqish (imloviy xatolarni kechirish uchun)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 2. Matnlarni birxillashtiruvchi PostgreSQL funksiyasi
CREATE OR REPLACE FUNCTION dwh.normalize_text(input_text TEXT)
RETURNS TEXT AS $$
BEGIN
    IF input_text IS NULL THEN
        RETURN '';
    END IF;
    
    -- Apostrof belgilarini birxillashtirish (oʻ, o‘, o’, o` -> o')
    input_text := REPLACE(input_text, 'oʻ', 'o''');
    input_text := REPLACE(input_text, 'o‘', 'o''');
    input_text := REPLACE(input_text, 'o’', 'o''');
    input_text := REPLACE(input_text, 'o`', 'o''');
    input_text := REPLACE(input_text, 'gʻ', 'g''');
    input_text := REPLACE(input_text, 'g‘', 'g''');
    input_text := REPLACE(input_text, 'g’', 'g''');
    input_text := REPLACE(input_text, 'g`', 'g''');
    
    -- Kichik harfga o'tkazish
    RETURN LOWER(TRIM(input_text));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- 3. dim_indicator jadvaliga tsvector qidiruv ustunini qo'shish
ALTER TABLE dwh.dim_indicator 
ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- 4. tsvector ustunini avtomatik to'ldiruvchi trigger funksiyasi
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

-- 5. Qidiruv indekslari (GIN):

-- A) Full-Text Search indeksi (tsvector)
CREATE INDEX IF NOT EXISTS idx_dim_indicator_fts 
ON dwh.dim_indicator USING gin (search_vector);

-- B) Trigram indekslari (imloga chidamli o'xshashlik qidiruvi - pg_trgm)
CREATE INDEX IF NOT EXISTS idx_dim_indicator_name_uz_trgm 
ON dwh.dim_indicator USING gin (dwh.normalize_text(name_uz) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_dim_indicator_name_ru_trgm 
ON dwh.dim_indicator USING gin (LOWER(name_ru) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_dim_item_name_uz_trgm 
ON dwh.dim_item USING gin (dwh.normalize_text(name_uz) gin_trgm_ops);
