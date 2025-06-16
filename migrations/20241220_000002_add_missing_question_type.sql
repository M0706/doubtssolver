-- Add question_type column if it doesn't exist
-- This handles cases where the database already existed before migrations were implemented

-- Add question_type column (PostgreSQL will ignore if it already exists with IF NOT EXISTS)
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS question_type VARCHAR(50);

-- Add subject_category column (PostgreSQL will ignore if it already exists with IF NOT EXISTS)  
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS subject_category VARCHAR(50); 