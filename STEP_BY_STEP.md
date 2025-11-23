# PostgreSQL Manual Execution Guide (Step by Step)

Execute the following commands in order while connected to PostgreSQL.

---

## Step 1: Feature 1 - Create suspect_clue table

```sql
CREATE TABLE IF NOT EXISTS suspect_clue (
    clue_id SERIAL PRIMARY KEY,
    incident_id INTEGER NOT NULL,
    suspect_id INTEGER NOT NULL,
    clue_text TEXT NOT NULL,
    clue_tsv TSVECTOR,
    FOREIGN KEY (incident_id) REFERENCES incident(incident_id) ON DELETE CASCADE,
    FOREIGN KEY (incident_id, suspect_id) REFERENCES suspect(incident_id, suspect_id) ON DELETE CASCADE
);
```

```sql
CREATE INDEX IF NOT EXISTS idx_suspect_clue_tsv_gin 
    ON suspect_clue USING GIN (clue_tsv);
```

```sql
CREATE INDEX IF NOT EXISTS idx_suspect_clue_incident_suspect 
    ON suspect_clue (incident_id, suspect_id);
```

---

## Step 2: Feature 2 - Add weapons column

```sql
ALTER TABLE suspect 
    ADD COLUMN IF NOT EXISTS weapons TEXT[];
```

```sql
CREATE INDEX IF NOT EXISTS idx_suspect_weapons_gin 
    ON suspect USING GIN (weapons);
```

---

## Step 3: Feature 3 - Create trigger function

```sql
CREATE OR REPLACE FUNCTION update_suspect_clue_tsv()
RETURNS TRIGGER AS $$
BEGIN
    NEW.clue_tsv := to_tsvector('english', COALESCE(NEW.clue_text, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## Step 4: Create triggers

```sql
DROP TRIGGER IF EXISTS trigger_suspect_clue_insert_tsv ON suspect_clue;
```

```sql
CREATE TRIGGER trigger_suspect_clue_insert_tsv
    BEFORE INSERT ON suspect_clue
    FOR EACH ROW
    EXECUTE FUNCTION update_suspect_clue_tsv();
```

```sql
DROP TRIGGER IF EXISTS trigger_suspect_clue_update_tsv ON suspect_clue;
```

```sql
CREATE TRIGGER trigger_suspect_clue_update_tsv
    BEFORE UPDATE ON suspect_clue
    FOR EACH ROW
    WHEN (OLD.clue_text IS DISTINCT FROM NEW.clue_text)
    EXECUTE FUNCTION update_suspect_clue_tsv();
```

---

## Step 5: Populate Data - Weapons Array

### 5-1. Robbery suspects (knife + handgun)

```sql
UPDATE suspect 
SET weapons = ARRAY['knife', 'handgun']
WHERE suspect_id IN (
    SELECT s.suspect_id
    FROM suspect s
    JOIN incident i ON s.incident_id = i.incident_id
    JOIN classified_as ca ON i.incident_id = ca.incident_id
    JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
    WHERE LOWER(ct.crime_type) LIKE '%robbery%'
    AND s.weapons IS NULL
    LIMIT 5
);
```

### 5-2. Assault suspects (knife)

```sql
UPDATE suspect 
SET weapons = ARRAY['knife']
WHERE suspect_id IN (
    SELECT s.suspect_id
    FROM suspect s
    JOIN incident i ON s.incident_id = i.incident_id
    JOIN classified_as ca ON i.incident_id = ca.incident_id
    JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
    WHERE LOWER(ct.crime_type) LIKE '%assault%'
    AND s.weapons IS NULL
    LIMIT 5
);
```

### 5-3. Burglary suspects (handgun)

```sql
UPDATE suspect 
SET weapons = ARRAY['handgun']
WHERE suspect_id IN (
    SELECT s.suspect_id
    FROM suspect s
    JOIN incident i ON s.incident_id = i.incident_id
    JOIN classified_as ca ON i.incident_id = ca.incident_id
    JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
    WHERE LOWER(ct.crime_type) LIKE '%burglary%'
    AND s.weapons IS NULL
    LIMIT 3
);
```

### 5-4. Burglary suspects (baseball_bat)

```sql
UPDATE suspect 
SET weapons = ARRAY['baseball_bat']
WHERE suspect_id IN (
    SELECT s.suspect_id
    FROM suspect s
    JOIN incident i ON s.incident_id = i.incident_id
    JOIN classified_as ca ON i.incident_id = ca.incident_id
    JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
    WHERE LOWER(ct.crime_type) LIKE '%burglary%'
    AND s.weapons IS NULL
    LIMIT 3
);
```

### 5-5. Kidnapping/Abduction suspects

```sql
UPDATE suspect 
SET weapons = ARRAY['blunt_object', 'rope']
WHERE suspect_id IN (
    SELECT s.suspect_id
    FROM suspect s
    JOIN incident i ON s.incident_id = i.incident_id
    JOIN classified_as ca ON i.incident_id = ca.incident_id
    JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
    WHERE (LOWER(ct.crime_type) LIKE '%kidnapping%' OR LOWER(ct.crime_type) LIKE '%abduction%')
    AND s.weapons IS NULL
    LIMIT 3
);
```

### 5-6. Additional assault suspects

```sql
UPDATE suspect 
SET weapons = ARRAY['blunt_object']
WHERE suspect_id IN (
    SELECT s.suspect_id
    FROM suspect s
    JOIN incident i ON s.incident_id = i.incident_id
    JOIN classified_as ca ON i.incident_id = ca.incident_id
    JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
    WHERE LOWER(ct.crime_type) LIKE '%assault%'
    AND s.weapons IS NULL
    LIMIT 2
);
```

### 5-7. Set all remaining suspects as unarmed

```sql
UPDATE suspect 
SET weapons = ARRAY[]::TEXT[]
WHERE weapons IS NULL;
```

---

## Step 6: Populate Data - Suspect Clues (at least 10)

### 6-1. Clue 1: Robbery suspect

```sql
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id, 
    'Wearing red hoodie with white stripes, black jeans, white sneakers. Has dragon tattoo on left forearm. Speaks with Brooklyn accent. Approximately 6 feet tall, medium build.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%robbery%'
LIMIT 1;
```

### 6-2. Clue 2: Assault suspect

```sql
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Male suspect, early 30s, short black hair, beard, wearing blue jacket. Has scar above right eyebrow. Carrying a black backpack. Last seen running north on 5th Avenue.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%assault%'
LIMIT 1;
```

### 6-3. Clue 3: Burglary suspect

```sql
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Suspect seen driving white sedan, license plate partially visible: ABC-12??. Wearing dark clothing, baseball cap. Exited vehicle and entered building through rear entrance. Approximately 5''10", thin build.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%burglary%'
LIMIT 1;
```

### 6-4. Clue 4: Theft suspect

```sql
INSERT INTO suspect_clue (incident_id, suspect_id, clue_text)
SELECT i.incident_id, s.suspect_id,
    'Female suspect, wearing red hoodie, carrying large tote bag. Has multiple ear piercings, visible tattoo on neck. Wearing sunglasses despite indoor location. Spoke with Queens accent.'
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE LOWER(ct.crime_type) LIKE '%theft%' OR LOWER(ct.crime_type) LIKE '%larceny%'
LIMIT 1;
```

### 6-5. Clue 5: Assault suspect (speech pattern)

```sql
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
```

### 6-6. Clue 6: Robbery suspect (vehicle)

```sql
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
```

### 6-7. Clue 7: Burglary suspect (detailed)

```sql
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
```

### 6-8. Clue 8: Assault suspect (distinctive features)

```sql
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
```

### 6-9. Clue 9: Theft suspect (clothing details)

```sql
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
```

### 6-10. Clue 10: Robbery suspect (comprehensive)

```sql
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
```

### 6-11. Clue 11: Additional clue

```sql
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
```

### 6-12. Clue 12: Another detailed clue

```sql
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
```

---

## Step 7: Verification

### 7-1. Check suspect_clue table

```sql
SELECT COUNT(*) FROM suspect_clue;
```
**Expected result:** >= 10

### 7-2. Check weapons column

```sql
SELECT COUNT(*) FROM suspect WHERE weapons IS NOT NULL;
```
**Expected result:** Should equal total number of suspect records

### 7-3. Check triggers

```sql
SELECT trigger_name FROM information_schema.triggers 
WHERE trigger_name LIKE '%suspect_clue%';
```
**Expected result:** 
- trigger_suspect_clue_insert_tsv
- trigger_suspect_clue_update_tsv

### 7-4. Sample data check

```sql
SELECT suspect_id, incident_id, weapons FROM suspect LIMIT 5;
```

```sql
SELECT clue_id, incident_id, suspect_id, LEFT(clue_text, 50) as clue_preview 
FROM suspect_clue LIMIT 5;
```

---

## Complete!

After completing all steps:
- ✅ `suspect_clue` table created
- ✅ `suspect.weapons` column added
- ✅ FTS triggers created
- ✅ At least 10 suspect_clue records
- ✅ All suspects have weapons values set

You can now run your Flask app and use the new features!
