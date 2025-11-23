-- ============================================================
-- Populate Database with Sample Data
-- ============================================================
-- This script populates:
-- 1. suspect_clue table with at least 10 tuples
-- 2. suspect.weapons array with meaningful values for existing suspects
-- ============================================================

-- ============================================================
-- Step 1: Populate weapons array for existing suspects
-- ============================================================
-- Update weapons for suspects based on crime types and realistic scenarios
-- We'll update at least 20 suspects with various weapons

UPDATE suspect 
SET weapons = ARRAY['knife', 'handgun']
WHERE incident_id IN (
    SELECT i.incident_id 
    FROM incident i
    JOIN classified_as ca ON i.incident_id = ca.incident_id
    JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
    WHERE LOWER(ct.crime_type) LIKE '%robbery%'
    LIMIT 5
)
AND weapons IS NULL
LIMIT 5;

UPDATE suspect 
SET weapons = ARRAY['knife']
WHERE incident_id IN (
    SELECT i.incident_id 
    FROM incident i
    JOIN classified_as ca ON i.incident_id = ca.incident_id
    JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
    WHERE LOWER(ct.crime_type) LIKE '%assault%'
    LIMIT 5
)
AND weapons IS NULL
LIMIT 5;

-- Burglary suspects with handgun
UPDATE suspect 
SET weapons = ARRAY['handgun']
WHERE incident_id IN (
    SELECT i.incident_id 
    FROM incident i
    JOIN classified_as ca ON i.incident_id = ca.incident_id
    JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
    WHERE LOWER(ct.crime_type) LIKE '%burglary%'
    LIMIT 5
)
AND weapons IS NULL
LIMIT 3;

-- Burglary suspects with baseball bat
UPDATE suspect 
SET weapons = ARRAY['baseball_bat']
WHERE incident_id IN (
    SELECT i.incident_id 
    FROM incident i
    JOIN classified_as ca ON i.incident_id = ca.incident_id
    JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
    WHERE LOWER(ct.crime_type) LIKE '%burglary%'
    LIMIT 5
)
AND weapons IS NULL
LIMIT 3;

UPDATE suspect 
SET weapons = ARRAY['blunt_object', 'rope']
WHERE incident_id IN (
    SELECT i.incident_id 
    FROM incident i
    JOIN classified_as ca ON i.incident_id = ca.incident_id
    JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
    WHERE LOWER(ct.crime_type) LIKE '%kidnapping%' OR LOWER(ct.crime_type) LIKE '%abduction%'
    LIMIT 3
)
AND weapons IS NULL
LIMIT 3;

-- Additional suspects with different weapons for variety
UPDATE suspect 
SET weapons = ARRAY['blunt_object']
WHERE incident_id IN (
    SELECT i.incident_id 
    FROM incident i
    JOIN classified_as ca ON i.incident_id = ca.incident_id
    JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
    WHERE LOWER(ct.crime_type) LIKE '%assault%'
    LIMIT 5
)
AND weapons IS NULL
LIMIT 2;

-- Set all remaining suspects with no weapons (unarmed)
-- This ensures all tuples have meaningful values for the weapons attribute
UPDATE suspect 
SET weapons = ARRAY[]::TEXT[]
WHERE weapons IS NULL;

-- ============================================================
-- Step 2: Insert at least 10 suspect_clue tuples
-- ============================================================
-- Get valid (incident_id, suspect_id) pairs first
-- Then insert rich narrative clues for full-text search

-- Clue 1: Robbery suspect with distinctive clothing
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id, 
    'Wearing red hoodie with white stripes, black jeans, white sneakers. Has dragon tattoo on left forearm. Speaks with Brooklyn accent. Approximately 6 feet tall, medium build.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%robbery%'
LIMIT 1;

-- Clue 2: Assault suspect with facial features
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Male suspect, early 30s, short black hair, beard, wearing blue jacket. Has scar above right eyebrow. Carrying a black backpack. Last seen running north on 5th Avenue.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%assault%'
LIMIT 1;

-- Clue 3: Burglary suspect with vehicle description
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Suspect seen driving white sedan, license plate partially visible: ABC-12??. Wearing dark clothing, baseball cap. Exited vehicle and entered building through rear entrance. Approximately 5''10", thin build.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%burglary%'
LIMIT 1;

-- Clue 4: Theft suspect with distinctive accessories
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Female suspect, wearing red hoodie, carrying large tote bag. Has multiple ear piercings, visible tattoo on neck. Wearing sunglasses despite indoor location. Spoke with Queens accent.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%theft%' OR LOWER(ct.crime_type) LIKE '%larceny%'
LIMIT 1;

-- Clue 5: Assault suspect with speech pattern
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Suspect wearing gray hoodie, black mask covering lower face. Has distinctive walk with slight limp. Spoke loudly with heavy New York accent. Wearing red sneakers, blue jeans.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%assault%'
  AND NOT EXISTS (
      SELECT 1 FROM suspect_clue sc 
      WHERE sc.incident_id = i.incident_id AND sc.suspect_id = s.suspect_id
  )
LIMIT 1;

-- Clue 6: Robbery suspect with vehicle and clothing
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Suspect fled scene in black SUV, tinted windows. Wearing red hoodie, black pants. Has visible tattoo on right hand. Approximately 25-30 years old, athletic build. Last seen heading west on Broadway.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%robbery%'
  AND NOT EXISTS (
      SELECT 1 FROM suspect_clue sc 
      WHERE sc.incident_id = i.incident_id AND sc.suspect_id = s.suspect_id
  )
LIMIT 1;

-- Clue 7: Burglary suspect with detailed description
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Male suspect, wearing dark blue hoodie with logo on front, black gloves, dark jeans. Carrying duffel bag. Has facial hair, wearing baseball cap pulled low. Approximately 6 feet tall.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%burglary%'
  AND NOT EXISTS (
      SELECT 1 FROM suspect_clue sc 
      WHERE sc.incident_id = i.incident_id AND sc.suspect_id = s.suspect_id
  )
LIMIT 1;

-- Clue 8: Assault suspect with distinctive features
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Suspect has dragon tattoo on left arm, wearing red hoodie, black mask. Spoke with distinctive voice, possibly Brooklyn accent. Wearing white sneakers, blue jeans. Carrying backpack.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%assault%'
  AND NOT EXISTS (
      SELECT 1 FROM suspect_clue sc 
      WHERE sc.incident_id = i.incident_id AND sc.suspect_id = s.suspect_id
  )
LIMIT 1;

-- Clue 9: Theft suspect with clothing details
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Female suspect, wearing red hoodie, black leggings, white sneakers. Has multiple visible tattoos on arms. Carrying large purse. Spoke quickly with Queens accent. Approximately 5''6", medium build.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE (LOWER(ct.crime_type) LIKE '%theft%' OR LOWER(ct.crime_type) LIKE '%larceny%')
  AND NOT EXISTS (
      SELECT 1 FROM suspect_clue sc 
      WHERE sc.incident_id = i.incident_id AND sc.suspect_id = s.suspect_id
  )
LIMIT 1;

-- Clue 10: Robbery suspect with comprehensive description
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Suspect wearing red hoodie with white stripes, black jeans, white sneakers. Has dragon tattoo visible on left forearm. Speaks with heavy Brooklyn accent. Approximately 6 feet tall, athletic build. Last seen running east on 42nd Street.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%robbery%'
  AND NOT EXISTS (
      SELECT 1 FROM suspect_clue sc 
      WHERE sc.incident_id = i.incident_id AND sc.suspect_id = s.suspect_id
  )
LIMIT 1;

-- Clue 11: Additional clue for variety
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Suspect has distinctive walk, slight limp on right side. Wearing gray hoodie, black mask, red sneakers. Spoke with New York accent. Has visible scar above left eyebrow. Carrying black backpack.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%assault%'
  AND NOT EXISTS (
      SELECT 1 FROM suspect_clue sc 
      WHERE sc.incident_id = i.incident_id AND sc.suspect_id = s.suspect_id
  )
LIMIT 1;

-- Clue 12: Another detailed clue
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Male suspect, wearing dark clothing, baseball cap. Has multiple tattoos on arms. Driving white sedan with tinted windows. Spoke with Brooklyn accent. Approximately 30 years old, medium build.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%burglary%'
  AND NOT EXISTS (
      SELECT 1 FROM suspect_clue sc 
      WHERE sc.incident_id = i.incident_id AND sc.suspect_id = s.suspect_id
  )
LIMIT 1;

-- Verify data was inserted
SELECT COUNT(*) as total_clues FROM suspect_clue;
SELECT COUNT(*) as suspects_with_weapons FROM suspect WHERE weapons IS NOT NULL AND array_length(weapons, 1) > 0;

