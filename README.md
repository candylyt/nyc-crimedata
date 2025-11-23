# NYC Crime Data - Advanced Features

## Team Information

**Team Members:**
- Yuting Liu (UNI: yl5961)
- Sally Go (UNI: yg3066)

**PostgreSQL Database for Grading:**
- **UNI: yl5961** (yl5961's database hosts the final schema)
- Database: `proj1part2`
- Host: `34.139.8.30`

---

## Overview

This project extends the NYC Crime Data database with three advanced features that enhance data modeling, search capabilities, and data integrity:

1. **Full-text suspect clues** with PostgreSQL Full-Text Search (FTS)
2. **Weapons array on suspects** for realistic multi-weapon modeling
3. **Automatic FTS maintenance trigger** for seamless index synchronization

---

## Feature 1: Full-Text Suspect Clues

### What We Added

- **New Table:** `suspect_clue`
  - `clue_id` (SERIAL PRIMARY KEY)
  - `incident_id` (INTEGER, FK to `incident`)
  - `suspect_id` (INTEGER, part of composite FK to `suspect`)
  - `clue_text` (TEXT) - Rich narrative descriptions
  - `clue_tsv` (TSVECTOR) - Full-text search vector (auto-generated)

- **Indexes:**
  - GIN index on `clue_tsv` for fast full-text searches
  - Composite index on `(incident_id, suspect_id)` for efficient lookups

### Why It's Meaningful

In real crime investigations, witness descriptions are rich, narrative text containing multiple details:
- Clothing descriptions ("red hoodie", "black jeans")
- Physical features ("dragon tattoo", "scar above eyebrow")
- Speech patterns ("Brooklyn accent", "spoke loudly")
- Behavioral details ("distinctive walk", "slight limp")

Traditional exact-match queries fail for such data. Full-text search enables investigators to:
- Search for "red hoodie tattoo" and find all suspects matching those terms
- Query natural language descriptions without knowing exact phrasing
- Combine multiple search terms efficiently using PostgreSQL's FTS operators

### Integration with Existing Schema

The `suspect_clue` table integrates naturally:
- **Foreign Key to `incident`**: Links clues to specific incidents
- **Composite Foreign Key to `suspect`**: Ensures clues belong to valid suspects within the incident
- **CASCADE DELETE**: When an incident or suspect is deleted, associated clues are automatically removed

This maintains referential integrity while allowing multiple clues per suspect (e.g., different witness accounts).

---

## Feature 2: Weapons Array on Suspects

### What We Added

- **New Column:** `suspect.weapons` (TEXT[])
  - Array type allowing multiple weapons per suspect
  - Can store values like: `ARRAY['knife', 'handgun']`, `ARRAY['blunt_object']`, etc.

- **Index:**
  - GIN index on `weapons` array for efficient array-based queries

### Why It's Meaningful

Real-world crime scenarios often involve multiple weapons:
- A suspect may carry both a knife and a handgun
- Different weapons may be used at different stages of a crime
- Some suspects are unarmed (empty array)

The array type enables:
- **Containment queries** (`@>`): Find all suspects carrying a specific weapon
- **Overlap queries** (`&&`): Find suspects with any weapon from a set
- **Array element access**: Query specific positions in the array
- **Realistic modeling**: One suspect can have multiple weapons without normalization

### Integration with Existing Schema

The `weapons` column is added directly to the existing `suspect` table:
- **No schema changes** to other tables required
- **Backward compatible**: Existing suspects have `NULL` or empty arrays
- **Natural fit**: Weapons are a property of suspects, not separate entities

This avoids creating a separate `suspect_weapon` junction table, which would be over-normalized for this use case.

---

## Feature 3: Automatic FTS Maintenance Trigger

### What We Added

- **Function:** `update_suspect_clue_tsv()`
  - Automatically generates `clue_tsv` from `clue_text` using `to_tsvector('english', ...)`

- **Triggers:**
  - `trigger_suspect_clue_insert_tsv`: BEFORE INSERT
  - `trigger_suspect_clue_update_tsv`: BEFORE UPDATE (only when `clue_text` changes)

### What It Does & Why It Exists

**Purpose:** Automatically maintain the `clue_tsv` column whenever a clue is inserted or updated, ensuring the GIN index stays synchronized with the text data.

**Why it's needed:**
- Without the trigger, administrators would need to manually call `to_tsvector()` every time
- Manual updates are error-prone and easy to forget
- The trigger ensures data consistency automatically

### Real Example Event: INSERT

**Scenario:** An administrator adds a new suspect clue through the web interface.

**What happens:**
1. Administrator submits form with:
   - `incident_id = 123`
   - `suspect_id = 5`
   - `clue_text = "Wearing red hoodie with white stripes, has dragon tattoo on left arm, speaks with Brooklyn accent"`

2. **BEFORE INSERT trigger fires:**
   - `update_suspect_clue_tsv()` function executes
   - Function reads `NEW.clue_text`
   - Computes: `NEW.clue_tsv = to_tsvector('english', 'Wearing red hoodie with white stripes, has dragon tattoo on left arm, speaks with Brooklyn accent')`
   - Returns modified `NEW` row with `clue_tsv` populated

3. **INSERT executes:**
   - Row inserted into `suspect_clue` table with:
     - `clue_id = 15` (auto-generated)
     - `incident_id = 123`
     - `suspect_id = 5`
     - `clue_text = "Wearing red hoodie with white stripes, has dragon tattoo on left arm, speaks with Brooklyn accent"`
     - `clue_tsv = 'accent':8 'arm':7 'brooklyn':8 'dragon':5 'hoodie':2 'left':6 'red':1 'speaks':8 'stripes':4 'tattoo':5 'white':3 'wearing':1`

4. **GIN index automatically updated:**
   - PostgreSQL updates the GIN index on `clue_tsv` to include the new vector
   - Full-text searches can now immediately find this clue

**Resulting table changes:**
- `suspect_clue` table: +1 row (clue_id=15)
- GIN index on `clue_tsv`: Updated with new vector entry

### Real Example Event: UPDATE

**Scenario:** Administrator corrects a typo in an existing clue.

**What happens:**
1. Administrator updates clue_id=15:
   - Old: `clue_text = "Wearing red hoodie with white stripes, has dragon tattoo on left arm"`
   - New: `clue_text = "Wearing red hoodie with white stripes, has dragon tattoo on left forearm"` (corrected "arm" to "forearm")

2. **BEFORE UPDATE trigger fires:**
   - `trigger_suspect_clue_update_tsv` checks: `OLD.clue_text IS DISTINCT FROM NEW.clue_text` → TRUE
   - `update_suspect_clue_tsv()` function executes
   - Computes: `NEW.clue_tsv = to_tsvector('english', 'Wearing red hoodie with white stripes, has dragon tattoo on left forearm')`
   - Returns modified `NEW` row

3. **UPDATE executes:**
   - Row updated in `suspect_clue`:
     - `clue_text` changed to new value
     - `clue_tsv` updated to: `'forearm':7 'hoodie':2 'red':1 ...` (note: "forearm" replaces "arm")

4. **GIN index automatically updated:**
   - Old vector removed from index
   - New vector added to index

**Resulting table changes:**
- `suspect_clue` table: Row 15 updated (clue_text and clue_tsv both changed)
- GIN index on `clue_tsv`: Old vector removed, new vector added

---

## SQL Queries

### Query 1: Full-Text Search for Suspect Clues

**Query:**
```sql
-- Find all suspect clues mentioning "red hoodie" AND "tattoo"
SELECT 
    sc.clue_id,
    sc.incident_id,
    sc.suspect_id,
    sc.clue_text,
    s.gender,
    s.race,
    s.age_grp,
    ct.crime_type
FROM suspect_clue sc
JOIN suspect s ON sc.incident_id = s.incident_id AND sc.suspect_id = s.suspect_id
JOIN incident i ON sc.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE sc.clue_tsv @@ to_tsquery('english', 'red & hoodie & tattoo')
ORDER BY sc.clue_id;
```

**Explanation:**
This query uses PostgreSQL's full-text search operator (`@@`) to find all suspect clues containing the terms "red", "hoodie", and "tattoo" in any order. The `to_tsquery()` function creates a search query that requires all three terms to be present, enabling investigators to quickly find suspects matching multiple descriptive criteria without exact phrase matching.

### Query 2: Array-Based Weapons Query

**Query:**
```sql
-- Find all suspects who carried a handgun, along with their incident details
SELECT 
    s.suspect_id,
    s.incident_id,
    s.gender,
    s.race,
    s.age_grp,
    s.weapons,
    ct.crime_type,
    i.occurred_date,
    a.borough
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN address a ON i.address_id = a.address_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE s.weapons @> ARRAY['handgun']::TEXT[]
ORDER BY i.occurred_date DESC;
```

**Explanation:**
This query uses the array containment operator (`@>`) to find all suspects whose `weapons` array contains 'handgun'. The query joins with incident, address, and crime type tables to provide comprehensive context, helping law enforcement identify patterns in handgun-related crimes across different locations and time periods.

---

## Database Setup Instructions

### 1. Run Migrations

```bash
psql -h 34.139.8.30 -U yl5961 -d proj1part2 -f migrations.sql
```

Password: `115674`

### 2. Populate Sample Data

```bash
psql -h 34.139.8.30 -U yl5961 -d proj1part2 -f populate_data.sql
```

This will:
- Add weapons arrays to at least 20 existing suspects
- Insert at least 12 suspect clues with rich narrative descriptions
- Verify data was inserted correctly

### 3. Verify Installation

```sql
-- Check suspect_clue table
SELECT COUNT(*) FROM suspect_clue;  -- Should be >= 10

-- Check weapons column
SELECT COUNT(*) FROM suspect WHERE weapons IS NOT NULL;  -- Should be >= 20

-- Check trigger exists
SELECT trigger_name FROM information_schema.triggers 
WHERE trigger_name LIKE '%suspect_clue%';
```

---

## Files

- `migrations.sql` - Creates tables, indexes, and triggers
- `populate_data.sql` - Populates sample data
- `server.py` - Flask application with admin interface for managing clues and weapons
- `templates/admin_detail.html` - UI for adding/editing clues and weapons

---

## Notes

- All triggers automatically maintain data consistency
- GIN indexes ensure fast queries even with large datasets
- Foreign key constraints maintain referential integrity
- CASCADE deletes ensure no orphaned records

