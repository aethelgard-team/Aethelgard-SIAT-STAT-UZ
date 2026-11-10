-- =============================================================================
-- 03_facts.sql: Fakt jadvali (fact_value)
-- =============================================================================

CREATE TABLE IF NOT EXISTS dwh.fact_value (
    fact_id BIGSERIAL PRIMARY KEY,
    indicator_id INTEGER NOT NULL REFERENCES dwh.dim_indicator(indicator_id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES dwh.dim_item(item_id) ON DELETE CASCADE,
    period_key VARCHAR(20) NOT NULL REFERENCES dwh.dim_period(period_key),
    
    value NUMERIC(20, 4),                       -- Tahlil uchun tozalangan haqiqiy son (agar 0.0 'mavjud emas' bo'lsa NULL)
    raw_value TEXT,                             -- JSON fayldan kelgan asl qiymat (o'zgarishsiz)
    status VARCHAR(30) DEFAULT 'valid',         -- 'valid', 'zero_marked', 'missing', 'calculated'
    snapshot_date DATE NOT NULL,                -- Ma'lumot qaysi kundagi snapshot ekanligi
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Bir xil ma'lumot qayta yuklanganda dublikat hosil bo'lmasligi (Upsert) uchun:
    CONSTRAINT uq_fact_indicator_item_period_snapshot UNIQUE (indicator_id, item_id, period_key, snapshot_date)
);

-- Tezkor SQL hisob-kitoblar va filtrlash uchun indekslar:
CREATE INDEX IF NOT EXISTS idx_fact_indicator_period ON dwh.fact_value(indicator_id, period_key);
CREATE INDEX IF NOT EXISTS idx_fact_item_period ON dwh.fact_value(item_id, period_key);
CREATE INDEX IF NOT EXISTS idx_fact_snapshot ON dwh.fact_value(snapshot_date);
