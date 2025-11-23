-- ============================================================
-- Advanced Features Migration Script
-- ============================================================
-- This script adds 3 advanced features:
-- 1. Full-text suspect clues table with GIN index
-- 2. Weapons array on suspects with GIN index
-- 3. Trigger for automatic FTS maintenance
-- ============================================================

-- ============================================================
-- Feature 1: Full-text suspect clues table
-- ============================================================
CREATE TABLE IF NOT EXISTS suspect_clue (
    clue_id SERIAL PRIMARY KEY,
    incident_id INTEGER NOT NULL,
    suspect_id INTEGER NOT NULL,
    clue_text TEXT NOT NULL,
    clue_tsv TSVECTOR,
    FOREIGN KEY (incident_id) REFERENCES incident(incident_id) ON DELETE CASCADE,
    -- Suspect table has composite PRIMARY KEY (incident_id, suspect_id)
    FOREIGN KEY (incident_id, suspect_id) REFERENCES suspect(incident_id, suspect_id) ON DELETE CASCADE
);

-- GIN index for full-text search on clue_tsv
CREATE INDEX IF NOT EXISTS idx_suspect_clue_tsv_gin 
    ON suspect_clue USING GIN (clue_tsv);

-- Index for faster lookups by incident_id and suspect_id
CREATE INDEX IF NOT EXISTS idx_suspect_clue_incident_suspect 
    ON suspect_clue (incident_id, suspect_id);

-- ============================================================
-- Feature 2: Weapons array on suspects
-- ============================================================
-- Add weapons column to suspect table
ALTER TABLE suspect 
    ADD COLUMN IF NOT EXISTS weapons TEXT[];

-- GIN index for array-based queries on weapons
CREATE INDEX IF NOT EXISTS idx_suspect_weapons_gin 
    ON suspect USING GIN (weapons);

-- ============================================================
-- Feature 3: Trigger for FTS maintenance
-- ============================================================
-- Function to automatically update clue_tsv from clue_text
CREATE OR REPLACE FUNCTION update_suspect_clue_tsv()
RETURNS TRIGGER AS $$
BEGIN
    -- Automatically generate tsvector from clue_text
    NEW.clue_tsv := to_tsvector('english', COALESCE(NEW.clue_text, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger BEFORE INSERT: automatically populate clue_tsv
DROP TRIGGER IF EXISTS trigger_suspect_clue_insert_tsv ON suspect_clue;
CREATE TRIGGER trigger_suspect_clue_insert_tsv
    BEFORE INSERT ON suspect_clue
    FOR EACH ROW
    EXECUTE FUNCTION update_suspect_clue_tsv();

-- Trigger BEFORE UPDATE: automatically update clue_tsv when clue_text changes
DROP TRIGGER IF EXISTS trigger_suspect_clue_update_tsv ON suspect_clue;
CREATE TRIGGER trigger_suspect_clue_update_tsv
    BEFORE UPDATE ON suspect_clue
    FOR EACH ROW
    WHEN (OLD.clue_text IS DISTINCT FROM NEW.clue_text)
    EXECUTE FUNCTION update_suspect_clue_tsv();

-- ============================================================
-- Optional: Update existing rows (if any) to populate clue_tsv
-- ============================================================
UPDATE suspect_clue 
SET clue_tsv = to_tsvector('english', COALESCE(clue_text, ''))
WHERE clue_tsv IS NULL;

