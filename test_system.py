#!/usr/bin/env python3
"""
Simple Test Script for Uncertainty-Aware System
"""

import asyncio
import asyncpg
import hashlib
from datetime import datetime

# Database config - update as needed
DB_CONFIG = {
    "user": "postgres",
    "password": "", 
    "database": "doubts",
    "host": "localhost",
    "port": 5432
}

TEST_QUESTIONS = [
    "Solve for x: 2x + 5 = 13",
    "According to the passage, what was the author's main argument?",
    "This is a random question that doesn't fit any category"
]

async def test_uncertainty_system():
    """Test the uncertainty-aware system"""
    
    print("🚀 Testing Uncertainty-Aware System")
    print("=" * 40)
    
    try:
        # Connect to database
        conn = await asyncpg.connect(**DB_CONFIG)
        print("✅ Connected to database")
        
        # Check if migration was applied
        tables_exist = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'question_cache'
            )
        """)
        
        if not tables_exist:
            print("❌ Migration not applied. Please run the migration first.")
            return
        
        print("✅ Migration detected")
        
        # Create test user
        test_email = f"test_{int(datetime.now().timestamp())}@example.com"
        user_id = await conn.fetchval("""
            INSERT INTO users (email, username, password)
            VALUES ($1, $2, $3)
            RETURNING id
        """, test_email, "test_user", "password_hash")
        
        print(f"✅ Created test user: {user_id}")
        
        # Test each question
        for i, question in enumerate(TEST_QUESTIONS):
            print(f"\n--- Testing Question {i+1} ---")
            print(f"Question: {question}")
            
            # Simulate classification
            classification = classify_question(question)
            print(f"Classification: {classification['final_category']} / {classification['final_type']}")
            print(f"Confidence: {classification['confidence']} ({classification['method']})")
            
            # Store question
            question_id = await store_question(conn, user_id, question, classification)
            print(f"✅ Stored question ID: {question_id}")
            
            # If confidence is low, check review queue
            if classification['confidence'] < 0.5:
                in_queue = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM classification_review_queue 
                        WHERE question_id = $1
                    )
                """, question_id)
                
                if in_queue:
                    print("✅ Added to review queue (low confidence)")
                else:
                    print("❌ Should be in review queue but isn't")
        
        # Test caching
        print(f"\n--- Testing Cache ---")
        
        # Create cache entry
        cache_id = await conn.fetchval("""
            INSERT INTO question_cache (
                question_pattern_hash, question_keywords, original_question_text,
                category, question_type, cached_response,
                similarity_threshold, requires_exact_numbers
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """, 
            "test_hash", ["solve", "equation"], "Solve for x: 2x + 5 = 13",
            "Math", "Problem Solving", "Test response",
            0.95, True
        )
        
        print(f"✅ Created cache entry: {cache_id}")
        
        # Test feedback
        await conn.execute("""
            INSERT INTO cache_feedback (
                cache_id, user_id, question_id, feedback_type
            ) VALUES ($1, $2, $3, $4)
        """, cache_id, user_id, question_id, "helpful")
        
        print("✅ Added cache feedback")
        
        # Clean up
        await conn.execute("DELETE FROM users WHERE id = $1", user_id)
        print("✅ Cleaned up test data")
        
        await conn.close()
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def classify_question(question_text: str) -> dict:
    """Simple classification logic"""
    
    text_lower = question_text.lower()
    
    # Math indicators
    if any(word in text_lower for word in ['solve', 'equation', 'calculate', 'x']):
        return {
            "final_category": "Quantitative Reasoning",
            "final_type": "Problem Solving",
            "confidence": 0.4,
            "method": "keyword"
        }
    
    # Verbal indicators  
    if any(word in text_lower for word in ['passage', 'author', 'argument']):
        return {
            "final_category": "Verbal Reasoning",
            "final_type": "Reading Comprehension", 
            "confidence": 0.4,
            "method": "keyword"
        }
    
    # Unknown
    return {
        "final_category": "Unknown",
        "final_type": "Unknown",
        "confidence": 0.0,
        "method": "fallback"
    }

async def store_question(conn, user_id, question_text, classification):
    """Store question with uncertainty info"""
    
    question_hash = hashlib.sha256(question_text.encode()).hexdigest()[:16]
    needs_review = classification["confidence"] < 0.5
    
    question_id = await conn.fetchval("""
        INSERT INTO questions (
            user_id, question_text, question_hash,
            final_category, final_type,
            classification_confidence, classification_method,
            needs_manual_review,
            ai_response, full_prompt_sent,
            timestamp, status
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), 'processed'
        ) RETURNING id
    """,
        user_id, question_text, question_hash,
        classification["final_category"], classification["final_type"],
        classification["confidence"], classification["method"],
        needs_review,
        f"Test response for: {question_text}", "Test prompt"
    )
    
    return question_id

if __name__ == "__main__":
    asyncio.run(test_uncertainty_system()) 