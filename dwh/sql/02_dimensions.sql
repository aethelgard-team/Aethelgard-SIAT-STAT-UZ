-- =============================================================================
-- 02_dimensions.sql: Yulduz sxema uchun o'lchov (Dimension) jadvallari
-- =============================================================================

-- 1. dim_indicator: SIAT statistik ko'rsatkichlari metama'lumotlari
CREATE TABLE IF NOT EXISTS dwh.dim_indicator (
    indicator_id INTEGER PRIMARY KEY,           -- SIAT dagi o'ziga xos ID (masalan, 1308)
    code TEXT,                                  -- Klassifikatsiya kodi (masalan, '1.11.03.0001')
    name_uz TEXT NOT NULL,                      -- O'zbekcha lotincha nomi
    name_ru TEXT,                               -- Ruscha nomi
    name_en TEXT,                               -- Inglizcha nomi
    name_uzc TEXT,                              -- O'zbekcha kirillcha nomi
    unit_uz TEXT,                               -- O'lchov birligi (uz)
    unit_ru TEXT,                               -- O'lchov birligi (ru)
    unit_en TEXT,                               -- O'lchov birligi (en)
    unit_uzc TEXT,                              -- O'lchov birligi (uzc)
    periodicity TEXT,                           -- Davriyligi (oylik, choraklik, yillik)
    organization TEXT,                          -- Mas'ul boshqarma / tashkilot
    methodology TEXT,                           -- Hisoblash metodikasi
    notes TEXT,                                 -- Qo'shimcha izohlar
    last_modified_date DATE,                    -- Oxirgi rasmiy o'zgartirilgan sana
    source_url TEXT,                            -- Manba URL havolasi
    is_cumulative BOOLEAN DEFAULT FALSE,        -- Jamlanma (yil boshidan o'suvchi) belgi
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. dim_item: Ko'rsatkich ichidagi klassifikator qatorlari (mahsulot, hudud, tarmoq...)
-- MUHIM QOIDA: item_code qat'iy ravishda VARCHAR/TEXT formatida saqlanadi ('001', '0040' larni yo'qotmaslik uchun)
CREATE TABLE IF NOT EXISTS dwh.dim_item (
    item_id SERIAL PRIMARY KEY,
    indicator_id INTEGER NOT NULL REFERENCES dwh.dim_indicator(indicator_id) ON DELETE CASCADE,
    item_code VARCHAR(100) NOT NULL,            -- QAT'IY MATN (TEXT): masalan '001', '1700'
    name_uz TEXT NOT NULL,                      -- Qatorning o'zbekcha nomi ('Mol go''shti')
    name_ru TEXT,                               -- Qatorning ruscha nomi ('Говядина')
    name_en TEXT,                               -- Qatorning inglizcha nomi ('Beef')
    name_uzc TEXT,                              -- Qatorning kirillcha nomi ('Мол гўшти')
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_indicator_item_code UNIQUE (indicator_id, item_code)
);

-- 3. dim_period: Vaqt davrlari (oy, chorak, yil)
CREATE TABLE IF NOT EXISTS dwh.dim_period (
    period_key VARCHAR(20) PRIMARY KEY,         -- Standartlashtirilgan kalit (masalan, '2026-M09', '2026-Q3', '2026')
    year INTEGER NOT NULL,                      -- Yil (masalan, 2026)
    quarter INTEGER,                            -- Chorak (1, 2, 3, 4 yoki NULL)
    month INTEGER,                              -- Oy (1..12 yoki NULL)
    period_type VARCHAR(20) NOT NULL,           -- 'monthly', 'quarterly', 'yearly', 'cumulative'
    start_date DATE,                            -- Davr boshlanish sanasi
    end_date DATE                               -- Davr tugash sanasi
);

-- Tezkor qidiruv uchun indekslar
CREATE INDEX IF NOT EXISTS idx_dim_item_indicator ON dwh.dim_item(indicator_id);
CREATE INDEX IF NOT EXISTS idx_dim_period_year ON dwh.dim_period(year);
