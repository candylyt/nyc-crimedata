-- ============================================================
-- SQL Queries for Advanced Features
-- ============================================================
-- These queries demonstrate the use of:
-- 1. Full-text search on suspect_clue table
-- 2. Array operations on suspect.weapons column
-- ============================================================

-- ============================================================
-- Query 1: Full-Text Search for Suspect Clues
-- ============================================================
-- Find all suspect clues mentioning "red hoodie" AND "tattoo"
-- This demonstrates PostgreSQL full-text search capabilities
SELECT 
    sc.clue_id,
    sc.incident_id,
    sc.suspect_id,
    sc.clue_text,
    s.gender,
    s.race,
    s.age_grp,
    ct.crime_type,
    i.occurred_date,
    a.borough
FROM suspect_clue sc
JOIN suspect s ON sc.incident_id = s.incident_id AND sc.suspect_id = s.suspect_id
JOIN incident i ON sc.incident_id = i.incident_id
JOIN address a ON i.address_id = a.address_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE sc.clue_tsv @@ to_tsquery('english', 'red & hoodie & tattoo')
ORDER BY sc.clue_id;

-- Explanation:
-- This query uses PostgreSQL's full-text search operator (@@) to find all 
-- suspect clues containing the terms "red", "hoodie", and "tattoo" in any order.
-- The to_tsquery() function creates a search query that requires all three terms 
-- to be present, enabling investigators to quickly find suspects matching multiple 
-- descriptive criteria without exact phrase matching.

-- ============================================================
-- Query 2: Array-Based Weapons Query
-- ============================================================
-- Find all suspects who carried a handgun, along with their incident details
-- This demonstrates PostgreSQL array containment operations
SELECT 
    s.suspect_id,
    s.incident_id,
    s.gender,
    s.race,
    s.age_grp,
    s.weapons,
    ct.crime_type,
    i.occurred_date,
    a.borough,
    a.postal_code
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN address a ON i.address_id = a.address_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE s.weapons @> ARRAY['handgun']::TEXT[]
ORDER BY i.occurred_date DESC;

-- Explanation:
-- This query uses the array containment operator (@>) to find all suspects whose 
-- weapons array contains 'handgun'. The query joins with incident, address, and crime 
-- type tables to provide comprehensive context, helping law enforcement identify 
-- patterns in handgun-related crimes across different locations and time periods.

-- ============================================================
-- Additional Example Queries
-- ============================================================

-- Example: Find suspects with multiple specific weapons
SELECT 
    s.suspect_id,
    s.incident_id,
    s.weapons,
    ct.crime_type
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE s.weapons @> ARRAY['knife', 'handgun']::TEXT[]
ORDER BY s.incident_id;

-- Example: Full-text search with OR conditions
SELECT 
    sc.clue_id,
    sc.clue_text,
    s.gender,
    s.race
FROM suspect_clue sc
JOIN suspect s ON sc.incident_id = s.incident_id AND sc.suspect_id = s.suspect_id
WHERE sc.clue_tsv @@ to_tsquery('english', 'hoodie | tattoo | accent')
ORDER BY sc.clue_id;

-- Example: Find suspects with any weapon from a set
SELECT 
    s.suspect_id,
    s.incident_id,
    s.weapons,
    ct.crime_type
FROM suspect s
JOIN incident i ON s.incident_id = i.incident_id
JOIN classified_as ca ON i.incident_id = ca.incident_id
JOIN crimetype ct ON ca.crime_type_id = ct.crime_type_id
WHERE s.weapons && ARRAY['handgun', 'knife', 'blunt_object']::TEXT[]
ORDER BY s.incident_id;

