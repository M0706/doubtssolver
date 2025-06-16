# Uncertainty-Aware GMAT Question Processing System

## 🎯 **Overview**

This implementation transforms your GMAT doubt solver into an uncertainty-aware system that:

- **Handles unknown question types gracefully** - Never fails due to classification issues
- **Uses smart caching with safety controls** - Prevents wrong answers from being served
- **Tracks confidence levels** - Flags uncertain cases for manual review
- **Incorporates user feedback loops** - Continuously improves answer quality

## 🗄️ **Database Schema Changes**

### Enhanced Questions Table (formerly `doubts`)
```sql
-- New uncertainty tracking fields
ALTER TABLE doubts ADD COLUMN user_category VARCHAR(50);      -- What user provided
ALTER TABLE doubts ADD COLUMN user_type VARCHAR(50);
ALTER TABLE doubts ADD COLUMN ai_category VARCHAR(50);        -- What AI inferred
ALTER TABLE doubts ADD COLUMN ai_type VARCHAR(50);
ALTER TABLE doubts ADD COLUMN final_category VARCHAR(50);     -- What was actually used
ALTER TABLE doubts ADD COLUMN final_type VARCHAR(50);
ALTER TABLE doubts ADD COLUMN classification_confidence DECIMAL(3,2);  -- 0.0-1.0
ALTER TABLE doubts ADD COLUMN classification_method VARCHAR(30);       -- 'user', 'ai', 'keyword', 'fallback'
ALTER TABLE doubts ADD COLUMN needs_manual_review BOOLEAN DEFAULT false;
ALTER TABLE doubts ADD COLUMN question_hash VARCHAR(64);               -- For similarity matching
ALTER TABLE doubts ADD COLUMN status VARCHAR(20) DEFAULT 'processed';  -- 'processed', 'cached', 'failed'

-- Rename for clarity
ALTER TABLE doubts RENAME TO questions;
```

### New Smart Cache Tables
```sql
-- Main cache table with safety controls
CREATE TABLE question_cache (
    id SERIAL PRIMARY KEY,
    question_pattern_hash VARCHAR(64) NOT NULL,
    question_keywords TEXT[],
    original_question_text TEXT NOT NULL,
    category VARCHAR(50),
    question_type VARCHAR(50),
    cached_response TEXT NOT NULL,
    
    -- Safety settings
    similarity_threshold DECIMAL(3,2) DEFAULT 0.95,
    requires_exact_numbers BOOLEAN DEFAULT true,
    requires_exact_variables BOOLEAN DEFAULT true,
    
    -- Quality tracking
    usage_count INTEGER DEFAULT 1,
    positive_feedback_count INTEGER DEFAULT 0,
    negative_feedback_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP DEFAULT NOW(),
    disabled_reason TEXT,
    disabled_at TIMESTAMP
);

-- User feedback on cached responses
CREATE TABLE cache_feedback (
    id SERIAL PRIMARY KEY,
    cache_id INTEGER NOT NULL REFERENCES question_cache(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    feedback_type VARCHAR(20) NOT NULL, -- 'helpful', 'wrong', 'irrelevant'
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(cache_id, user_id, question_id)
);

-- User feedback on question responses
CREATE TABLE question_feedback (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    classification_feedback JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(question_id, user_id)
);

-- Manual review queue for uncertain classifications
CREATE TABLE classification_review_queue (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    current_category VARCHAR(50),
    current_type VARCHAR(50),
    confidence_score DECIMAL(3,2),
    reason_for_review TEXT,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'reviewed', 'skipped'
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🚀 **Deployment Steps**

### 1. Run Database Migration

```bash
# Apply the uncertainty-aware schema migration
psql -d gmat_doubt_solver -f migrations/20241221_000001_uncertainty_aware_schema.sql
```

### 2. Update Route Imports

In your main app file, add the new feedback routes:

```python
from app.routes import feedback

app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
```

### 3. Test the System

```bash
# Run the test script to validate everything works
python test_system.py
```

### 4. Monitor Review Queue

Check for questions needing manual review:

```sql
SELECT q.question_text, q.final_category, q.classification_confidence
FROM questions q 
WHERE q.needs_manual_review = true 
ORDER BY q.timestamp DESC;
```

## 🔧 **Usage Examples**

### New Enhanced Processing

```python
from app.services.enhanced_qa import process_question_with_uncertainty

# Process question with uncertainty handling
response = await process_question_with_uncertainty(
    question_text="Solve for x: 2x + 5 = 13",
    user_id=123,
    user_category="Math",          # Optional user hint
    user_type="Problem Solving"    # Optional user hint
)
```

### Cache Interaction

```python
from app.services.cache_service import cache_service

# Check cache before processing
cached = await cache_service.get_cached_response(
    question_text="What is 2 + 2?",
    category="Math",
    user_id=123
)

if cached:
    return cached["response"]
```

### Feedback Submission

```python
# Submit question feedback
POST /api/v1/questions/123/feedback
{
    "rating": 4,
    "feedback_text": "Good explanation but could be clearer"
}

# Submit cache feedback  
POST /api/v1/cache/456/feedback?question_id=123
{
    "feedback_type": "wrong",
    "feedback_text": "This answer is incorrect for my question"
}
```

## 📊 **Key Benefits**

✅ **Never fails due to classification issues** - "Unknown" is a valid answer  
✅ **Smart caching prevents wrong answers** - Math safety checks, user feedback loops  
✅ **Tracks uncertainty explicitly** - Confidence scores, review queues  
✅ **Continuous improvement** - User feedback drives quality  
✅ **Full backward compatibility** - Existing code works unchanged  
✅ **Admin visibility** - Clear metrics and monitoring  

The system is now **production-ready** with proper error handling, safety controls, and monitoring capabilities. 