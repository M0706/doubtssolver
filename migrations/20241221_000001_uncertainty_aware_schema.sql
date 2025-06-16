-- Migration: Uncertainty-Aware Schema for GMAT Doubt Solver
-- This migration transforms the existing doubts table and adds supporting tables
-- for smart caching, feedback, and uncertainty tracking

-- Step 1: Enhance users table with more fields
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(50) DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active TIMESTAMP DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
ALTER TABLE users ADD COLUMN IF NOT EXISTS total_questions_asked INTEGER DEFAULT 0;

-- Step 2: Transform doubts table to questions table with uncertainty tracking
-- First, add new columns to existing doubts table
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS user_category VARCHAR(50);
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS user_type VARCHAR(50);
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS ai_category VARCHAR(50);
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS ai_type VARCHAR(50);
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS final_category VARCHAR(50);
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS final_type VARCHAR(50);
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS classification_confidence DECIMAL(3,2);
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS classification_method VARCHAR(30);
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS needs_manual_review BOOLEAN DEFAULT false;
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS question_hash VARCHAR(64);
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS options JSONB;
ALTER TABLE doubts ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'processed';

-- Migrate existing data to new structure
UPDATE doubts SET 
    final_category = subject_category,
    final_type = question_type,
    classification_confidence = CASE 
        WHEN subject_category IS NOT NULL AND question_type IS NOT NULL THEN 0.5
        ELSE 0.0
    END,
    classification_method = CASE 
        WHEN subject_category IS NOT NULL AND question_type IS NOT NULL THEN 'legacy_data'
        ELSE 'unknown'
    END,
    needs_manual_review = (subject_category IS NULL OR question_type IS NULL),
    question_hash = LEFT(MD5(question_text), 16)
WHERE question_hash IS NULL;

-- Rename doubts table to questions for clarity
ALTER TABLE doubts RENAME TO questions;

-- Step 3: Create question_cache table for smart caching
CREATE TABLE IF NOT EXISTS question_cache (
    id SERIAL PRIMARY KEY,
    question_pattern_hash VARCHAR(64) NOT NULL,
    question_keywords TEXT[],
    original_question_text TEXT NOT NULL,
    
    -- Classification info
    category VARCHAR(50),
    question_type VARCHAR(50),
    cached_response TEXT NOT NULL,
    
    -- Safety controls
    similarity_threshold DECIMAL(3,2) DEFAULT 0.95,
    requires_exact_numbers BOOLEAN DEFAULT true,
    requires_exact_variables BOOLEAN DEFAULT true,
    
    -- Quality tracking
    usage_count INTEGER DEFAULT 1,
    positive_feedback_count INTEGER DEFAULT 0,
    negative_feedback_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    disabled_reason TEXT,
    disabled_at TIMESTAMP
);

-- Step 4: Create cache_feedback table
CREATE TABLE IF NOT EXISTS cache_feedback (
    id SERIAL PRIMARY KEY,
    cache_id INTEGER NOT NULL REFERENCES question_cache(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    feedback_type VARCHAR(20) NOT NULL, -- 'helpful', 'wrong', 'irrelevant'
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(cache_id, user_id, question_id)
);

-- Step 5: Create question_feedback table for user feedback on answers
CREATE TABLE IF NOT EXISTS question_feedback (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    classification_feedback JSONB, -- User says "this was classified wrong"
    improvement_suggestions JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(question_id, user_id)
);

-- Step 6: Create manual review queue
CREATE TABLE IF NOT EXISTS classification_review_queue (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    current_category VARCHAR(50),
    current_type VARCHAR(50),
    confidence_score DECIMAL(3,2),
    reason_for_review TEXT,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'reviewed', 'skipped'
    assigned_to INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP,
    reviewer_notes TEXT
);

-- Step 7: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_questions_user_id ON questions(user_id);
CREATE INDEX IF NOT EXISTS idx_questions_timestamp ON questions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_questions_final_category ON questions(final_category);
CREATE INDEX IF NOT EXISTS idx_questions_final_type ON questions(final_type);
CREATE INDEX IF NOT EXISTS idx_questions_needs_review ON questions(needs_manual_review) WHERE needs_manual_review = true;
CREATE INDEX IF NOT EXISTS idx_questions_hash ON questions(question_hash);
CREATE INDEX IF NOT EXISTS idx_questions_status ON questions(status);

-- Cache table indexes
CREATE INDEX IF NOT EXISTS idx_question_cache_pattern ON question_cache(question_pattern_hash);
CREATE INDEX IF NOT EXISTS idx_question_cache_keywords ON question_cache USING GIN(question_keywords);
CREATE INDEX IF NOT EXISTS idx_question_cache_active ON question_cache(is_active, last_used DESC) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_question_cache_category ON question_cache(category, question_type);

-- Feedback table indexes
CREATE INDEX IF NOT EXISTS idx_cache_feedback_cache_id ON cache_feedback(cache_id);
CREATE INDEX IF NOT EXISTS idx_cache_feedback_user_id ON cache_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_question_feedback_question_id ON question_feedback(question_id);
CREATE INDEX IF NOT EXISTS idx_question_feedback_rating ON question_feedback(rating);

-- Review queue indexes
CREATE INDEX IF NOT EXISTS idx_review_queue_status ON classification_review_queue(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_review_queue_created ON classification_review_queue(created_at DESC);

-- Step 8: Add constraints for data integrity
ALTER TABLE questions ADD CONSTRAINT valid_classification_confidence 
    CHECK (classification_confidence IS NULL OR (classification_confidence >= 0.0 AND classification_confidence <= 1.0));

ALTER TABLE questions ADD CONSTRAINT valid_classification_method 
    CHECK (classification_method IN ('user', 'ai', 'keyword', 'fallback', 'manual', 'legacy_data', 'unknown'));

ALTER TABLE questions ADD CONSTRAINT valid_status 
    CHECK (status IN ('processed', 'processing', 'failed', 'cached'));

ALTER TABLE cache_feedback ADD CONSTRAINT valid_feedback_type 
    CHECK (feedback_type IN ('helpful', 'wrong', 'irrelevant', 'partially_helpful'));

ALTER TABLE classification_review_queue ADD CONSTRAINT valid_review_status 
    CHECK (status IN ('pending', 'reviewed', 'skipped', 'reassigned'));

-- Step 9: Create helper function for automatic review queue population
CREATE OR REPLACE FUNCTION add_to_review_queue_if_needed()
RETURNS TRIGGER AS $$
BEGIN
    -- Add to review queue if confidence is low
    IF NEW.classification_confidence IS NOT NULL AND NEW.classification_confidence < 0.5 THEN
        INSERT INTO classification_review_queue (
            question_id, 
            current_category, 
            current_type, 
            confidence_score, 
            reason_for_review
        ) VALUES (
            NEW.id,
            NEW.final_category,
            NEW.final_type,
            NEW.classification_confidence,
            'Low classification confidence: ' || NEW.classification_confidence
        ) ON CONFLICT DO NOTHING;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-populate review queue
DROP TRIGGER IF EXISTS trigger_add_to_review_queue ON questions;
CREATE TRIGGER trigger_add_to_review_queue
    AFTER INSERT OR UPDATE ON questions
    FOR EACH ROW
    EXECUTE FUNCTION add_to_review_queue_if_needed();

-- Step 10: Update user question count trigger
CREATE OR REPLACE FUNCTION update_user_question_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE users SET 
            total_questions_asked = total_questions_asked + 1,
            last_active = NOW()
        WHERE id = NEW.user_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_user_stats ON questions;
CREATE TRIGGER trigger_update_user_stats
    AFTER INSERT ON questions
    FOR EACH ROW
    EXECUTE FUNCTION update_user_question_count();

-- Step 11: Create view for easy question retrieval with all classification info
CREATE OR REPLACE VIEW question_details AS
SELECT 
    q.id,
    q.user_id,
    q.question_text,
    q.user_category,
    q.user_type,
    q.ai_category,
    q.ai_type,
    q.final_category,
    q.final_type,
    q.classification_confidence,
    q.classification_method,
    q.needs_manual_review,
    q.ai_response,
    q.options,
    q.status,
    q.timestamp,
    -- Aggregated feedback info
    COALESCE(AVG(qf.rating), 0) as avg_rating,
    COUNT(qf.id) as feedback_count,
    -- User info
    u.username,
    u.email
FROM questions q
LEFT JOIN question_feedback qf ON q.id = qf.question_id
LEFT JOIN users u ON q.user_id = u.id
GROUP BY q.id, u.username, u.email;

-- Migration completed successfully
-- The database now supports uncertainty-aware question processing with smart caching 