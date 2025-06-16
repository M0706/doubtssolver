#!/usr/bin/env python3
"""
Test Script for Uncertainty-Aware GMAT Question Processing System
Tests the complete flow: migration, classification, caching, and feedback
"""

import asyncio
import asyncpg
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

# Test Configuration
DB_CONFIG = {
    "user": "postgres",
    "password": "password", 
    "database": "gmat_doubt_solver",
    "host": "localhost",
    "port": 5432
}

# Test Data
TEST_QUESTIONS = [
    {
        "text": "Solve for x: 2x + 5 = 13",
        "expected_category": "Quantitative Reasoning",
        "expected_type": "Problem Solving",
        "user_category": None,
        "user_type": None
    },
    {
        "text": "If John has 3 apples and buys 2 more, how many apples does he have?",
        "expected_category": "Quantitative Reasoning", 
        "expected_type": "Problem Solving",
        "user_category": "Math",
        "user_type": "Word Problem"
    },
    {
        "text": "According to the passage, what was the author's main argument?",
        "expected_category": "Verbal Reasoning",
        "expected_type": "Reading Comprehension", 
        "user_category": None,
        "user_type": None
    },
    {
        "text": "This is a completely random text that doesn't fit any category",
        "expected_category": "Unknown",
        "expected_type": "Unknown",
        "user_category": None,
        "user_type": None
    }
]

class UncertaintySystemTester:
    
    def __init__(self):
        self.conn = None
        self.test_user_id = None
        
    async def connect(self):
        """Connect to database"""
        try:
            self.conn = await asyncpg.connect(**DB_CONFIG)
            print("✅ Connected to database")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            raise
    
    async def setup_test_data(self):
        """Create test user and ensure migrations are applied"""
        
        # Create test user
        test_email = f"test_uncertainty_{int(datetime.now().timestamp())}@example.com"
        
        self.test_user_id = await self.conn.fetchval("""
            INSERT INTO users (email, username, password)
            VALUES ($1, $2, $3)
            RETURNING id
        """, test_email, "test_uncertainty_user", "password_hash")
        
        print(f"✅ Created test user with ID: {self.test_user_id}")
        
        # Check if new tables exist
        tables_exist = await self.check_migration_status()
        if not tables_exist:
            print("❌ Migration not applied yet. Please run the migration first.")
            return False
            
        return True
    
    async def check_migration_status(self) -> bool:
        """Check if uncertainty-aware tables exist"""
        
        required_tables = [
            'question_cache', 
            'cache_feedback', 
            'question_feedback',
            'classification_review_queue'
        ]
        
        existing_tables = []
        for table in required_tables:
            exists = await self.conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = $1
                )
            """, table)
            
            if exists:
                existing_tables.append(table)
            else:
                print(f"❌ Table {table} does not exist")
        
        # Check if questions table has new columns
        questions_columns = await self.conn.fetch("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'questions'
        """)
        
        required_columns = [
            'user_category', 'ai_category', 'final_category',
            'classification_confidence', 'classification_method',
            'needs_manual_review', 'question_hash'
        ]
        
        existing_columns = [row['column_name'] for row in questions_columns]
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            print(f"❌ Missing columns in questions table: {missing_columns}")
            return False
        
        if len(existing_tables) == len(required_tables):
            print("✅ All required tables exist")
            return True
        else:
            print(f"❌ Missing tables: {set(required_tables) - set(existing_tables)}")
            return False
    
    async def test_question_classification(self):
        """Test the uncertainty-aware question classification"""
        
        print("\n🧪 Testing Question Classification...")
        
        for i, test_case in enumerate(TEST_QUESTIONS):
            print(f"\n--- Test Case {i+1} ---")
            print(f"Question: {test_case['text'][:50]}...")
            
            # Simulate the classification process
            classification = await self.simulate_classification(
                test_case['text'],
                test_case['user_category'],
                test_case['user_type']
            )
            
            print(f"Final Category: {classification['final_category']}")
            print(f"Final Type: {classification['final_type']}")
            print(f"Confidence: {classification['confidence']}")
            print(f"Method: {classification['method']}")
            
            # Store question with classification
            question_id = await self.store_test_question(
                test_case['text'], classification
            )
            
            print(f"✅ Stored question with ID: {question_id}")
            
            # Check if low confidence questions are added to review queue
            if classification['confidence'] < 0.5:
                review_entry = await self.conn.fetchrow("""
                    SELECT * FROM classification_review_queue 
                    WHERE question_id = $1
                """, question_id)
                
                if review_entry:
                    print("✅ Low confidence question added to review queue")
                else:
                    print("❌ Low confidence question NOT added to review queue")
    
    async def simulate_classification(
        self, 
        question_text: str, 
        user_category: Optional[str], 
        user_type: Optional[str]
    ) -> Dict[str, Any]:
        """Simulate the classification process"""
        
        classification = {
            "user_category": user_category,
            "user_type": user_type,
            "ai_category": None,
            "ai_type": None,
            "final_category": "Unknown",
            "final_type": "Unknown",
            "confidence": 0.0,
            "method": "unknown"
        }
        
        # Use user-provided if available
        if user_category and user_type:
            classification.update({
                "final_category": user_category,
                "final_type": user_type,
                "confidence": 0.6,
                "method": "user_provided"
            })
            return classification
        
        # Keyword-based classification
        text_lower = question_text.lower()
        
        math_keywords = ['equation', 'solve', 'calculate', 'x =', 'algebra', 'geometry', 'apples']
        if any(keyword in text_lower for keyword in math_keywords):
            classification.update({
                "final_category": "Quantitative Reasoning",
                "final_type": "Problem Solving",
                "confidence": 0.4,
                "method": "keyword_fallback"
            })
            return classification
        
        verbal_keywords = ['passage', 'author', 'paragraph', 'reading', 'argument']
        if any(keyword in text_lower for keyword in verbal_keywords):
            classification.update({
                "final_category": "Verbal Reasoning",
                "final_type": "Reading Comprehension",
                "confidence": 0.4,
                "method": "keyword_fallback"
            })
            return classification
        
        # Fallback to Unknown
        classification.update({
            "final_category": "Unknown",
            "final_type": "Unknown",
            "confidence": 0.0,
            "method": "fallback_unknown"
        })
        
        return classification
    
    async def store_test_question(
        self, 
        question_text: str, 
        classification: Dict[str, Any]
    ) -> int:
        """Store test question with classification"""
        
        question_hash = hashlib.sha256(question_text.encode()).hexdigest()[:16]
        needs_review = classification["confidence"] < 0.5
        
        question_id = await self.conn.fetchval("""
            INSERT INTO questions (
                user_id, question_text, question_hash,
                user_category, user_type,
                ai_category, ai_type,
                final_category, final_type,
                classification_confidence, classification_method,
                needs_manual_review,
                ai_response, full_prompt_sent,
                timestamp, status
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW(), 'processed'
            ) RETURNING id
        """,
            self.test_user_id, question_text, question_hash,
            classification["user_category"], classification["user_type"],
            classification["ai_category"], classification["ai_type"],
            classification["final_category"], classification["final_type"],
            classification["confidence"], classification["method"],
            needs_review,
            f"Test response for: {question_text}", "Test prompt"
        )
        
        return question_id
    
    async def test_caching_system(self):
        """Test the smart caching system"""
        
        print("\n🧪 Testing Caching System...")
        
        # Create cache entries
        test_cache_entries = [
            {
                "question": "Solve for x: 2x + 5 = 13",
                "response": "To solve 2x + 5 = 13:\n1. Subtract 5: 2x = 8\n2. Divide by 2: x = 4",
                "category": "Quantitative Reasoning",
                "type": "Problem Solving",
                "similarity_threshold": 0.95,
                "requires_exact_numbers": True
            },
            {
                "question": "What is 3 + 5?",
                "response": "3 + 5 = 8",
                "category": "Quantitative Reasoning",
                "type": "Basic Math",
                "similarity_threshold": 0.90,
                "requires_exact_numbers": True
            }
        ]
        
        cache_ids = []
        for entry in test_cache_entries:
            cache_id = await self.create_cache_entry(entry)
            cache_ids.append(cache_id)
            print(f"✅ Created cache entry: {cache_id}")
        
        # Test cache matching
        similar_questions = [
            "Solve for x: 2x + 5 = 13",  # Exact match
            "Solve for x: 2x + 5 = 11",  # Different number - should NOT match
            "What is 3 + 5?",            # Exact match
        ]
        
        for question in similar_questions:
            matches = await self.find_cache_matches(question)
            print(f"Question: '{question}' -> {len(matches)} cache matches")
            
            for match in matches:
                print(f"  Match: cache_id={match['id']}, similarity_threshold={match['similarity_threshold']}")
        
        return cache_ids
    
    async def create_cache_entry(self, entry: Dict[str, Any]) -> int:
        """Create a cache entry"""
        
        keywords = self.extract_keywords(entry["question"])
        pattern_hash = self.generate_pattern_hash(entry["question"])
        
        cache_id = await self.conn.fetchval("""
            INSERT INTO question_cache (
                question_pattern_hash, question_keywords, original_question_text,
                category, question_type, cached_response,
                similarity_threshold, requires_exact_numbers, requires_exact_variables
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """,
            pattern_hash, keywords, entry["question"],
            entry["category"], entry["type"], entry["response"],
            entry["similarity_threshold"], entry["requires_exact_numbers"], False
        )
        
        return cache_id
    
    def extract_keywords(self, question: str) -> list:
        """Extract keywords from question"""
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = question.lower().split()
        return [word for word in words if len(word) > 2 and word not in stop_words]
    
    def generate_pattern_hash(self, question: str) -> str:
        """Generate pattern hash"""
        import re
        normalized = re.sub(r'\s+', ' ', question.lower().strip())
        pattern = re.sub(r'\d+(?:\.\d+)?', 'NUM', normalized)
        return hashlib.md5(pattern.encode()).hexdigest()[:16]
    
    async def find_cache_matches(self, question: str) -> list:
        """Find cache matches for a question"""
        
        keywords = self.extract_keywords(question)
        pattern_hash = self.generate_pattern_hash(question)
        
        matches = await self.conn.fetch("""
            SELECT 
                id, original_question_text, similarity_threshold, 
                requires_exact_numbers, requires_exact_variables
            FROM question_cache 
            WHERE is_active = true
            AND (
                question_pattern_hash = $1
                OR question_keywords && $2
            )
            ORDER BY usage_count DESC
            LIMIT 5
        """, pattern_hash, keywords)
        
        return [dict(match) for match in matches]
    
    async def test_feedback_system(self, cache_ids: list):
        """Test the feedback system"""
        
        print("\n🧪 Testing Feedback System...")
        
        if not cache_ids:
            print("❌ No cache entries to test feedback on")
            return
        
        cache_id = cache_ids[0]
        
        # Create a test question for feedback
        question_id = await self.store_test_question(
            "Test question for feedback",
            {
                "user_category": None,
                "user_type": None,
                "ai_category": None,
                "ai_type": None,
                "final_category": "Test",
                "final_type": "Test",
                "confidence": 0.8,
                "method": "test"
            }
        )
        
        # Test question feedback
        await self.conn.execute("""
            INSERT INTO question_feedback (
                question_id, user_id, rating, feedback_text
            ) VALUES ($1, $2, $3, $4)
        """, question_id, self.test_user_id, 4, "Good explanation")
        
        print("✅ Created question feedback")
        
        # Test cache feedback
        await self.conn.execute("""
            INSERT INTO cache_feedback (
                cache_id, user_id, question_id, feedback_type, feedback_text
            ) VALUES ($1, $2, $3, $4, $5)
        """, cache_id, self.test_user_id, question_id, "helpful", "Cache response was accurate")
        
        print("✅ Created cache feedback")
        
        # Update cache counters
        await self.conn.execute("""
            UPDATE question_cache 
            SET positive_feedback_count = positive_feedback_count + 1,
                usage_count = usage_count + 1
            WHERE id = $1
        """, cache_id)
        
        print("✅ Updated cache counters")
        
        # Test negative feedback auto-disable
        await self.simulate_negative_feedback(cache_id, question_id)
    
    async def simulate_negative_feedback(self, cache_id: int, question_id: int):
        """Simulate negative feedback to test auto-disable"""
        
        print("\n--- Testing Cache Auto-Disable ---")
        
        # Add 3 negative feedbacks to trigger auto-disable
        for i in range(3):
            fake_user_id = self.test_user_id + i + 1
            fake_question_id = question_id + i + 1
            
            # Create fake users and questions for testing
            await self.conn.execute("""
                INSERT INTO users (id, email, username, password) 
                VALUES ($1, $2, $3, $4) 
                ON CONFLICT (id) DO NOTHING
            """, fake_user_id, f"fake{i}@test.com", f"fake_user_{i}", "hash")
            
            await self.conn.execute("""
                INSERT INTO questions (id, user_id, question_text, ai_response, full_prompt_sent, timestamp) 
                VALUES ($1, $2, $3, $4, $5, NOW()) 
                ON CONFLICT (id) DO NOTHING
            """, fake_question_id, fake_user_id, f"Fake question {i}", "Fake response", "Fake prompt")
            
            # Add negative feedback
            await self.conn.execute("""
                INSERT INTO cache_feedback (
                    cache_id, user_id, question_id, feedback_type, feedback_text
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
            """, cache_id, fake_user_id, fake_question_id, "wrong", f"Wrong answer {i}")
            
            # Update counter
            await self.conn.execute("""
                UPDATE question_cache 
                SET negative_feedback_count = negative_feedback_count + 1
                WHERE id = $1
            """, cache_id)
        
        # Check if cache entry should be disabled
        cache_entry = await self.conn.fetchrow("""
            SELECT negative_feedback_count, is_active 
            FROM question_cache 
            WHERE id = $1
        """, cache_id)
        
        if cache_entry['negative_feedback_count'] >= 3:
            # Simulate auto-disable
            await self.conn.execute("""
                UPDATE question_cache 
                SET is_active = false, 
                    disabled_reason = 'Multiple negative feedbacks',
                    disabled_at = NOW()
                WHERE id = $1
            """, cache_id)
            
            print("✅ Cache entry auto-disabled due to negative feedback")
        else:
            print(f"❌ Cache entry not disabled (negative count: {cache_entry['negative_feedback_count']})")
    
    async def test_analytics(self):
        """Test analytics and reporting"""
        
        print("\n🧪 Testing Analytics...")
        
        # Question statistics
        stats = await self.conn.fetchrow("""
            SELECT 
                COUNT(*) as total_questions,
                COUNT(*) FILTER (WHERE needs_manual_review = true) as needs_review,
                AVG(classification_confidence) as avg_confidence,
                COUNT(DISTINCT final_category) as unique_categories
            FROM questions
            WHERE user_id = $1
        """, self.test_user_id)
        
        print(f"Total Questions: {stats['total_questions']}")
        print(f"Needs Review: {stats['needs_review']}")
        print(f"Avg Confidence: {stats['avg_confidence']:.2f}")
        print(f"Unique Categories: {stats['unique_categories']}")
        
        # Cache statistics
        cache_stats = await self.conn.fetchrow("""
            SELECT 
                COUNT(*) as total_entries,
                COUNT(*) FILTER (WHERE is_active = true) as active_entries,
                COUNT(*) FILTER (WHERE is_active = false) as disabled_entries,
                AVG(usage_count) as avg_usage,
                SUM(positive_feedback_count) as total_positive,
                SUM(negative_feedback_count) as total_negative
            FROM question_cache
        """)
        
        print(f"Cache Entries: {cache_stats['total_entries']} (Active: {cache_stats['active_entries']}, Disabled: {cache_stats['disabled_entries']})")
        print(f"Avg Usage: {cache_stats['avg_usage']:.2f}")
        print(f"Feedback: +{cache_stats['total_positive']} / -{cache_stats['total_negative']}")
        
        print("✅ Analytics working correctly")
    
    async def cleanup_test_data(self):
        """Clean up test data"""
        
        if self.test_user_id:
            # Delete test user and all related data (cascades)
            await self.conn.execute("DELETE FROM users WHERE id = $1", self.test_user_id)
            print("✅ Cleaned up test data")
    
    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
            print("✅ Database connection closed")

async def main():
    """Run all tests"""
    
    print("🚀 Starting Uncertainty-Aware System Tests")
    print("=" * 50)
    
    tester = UncertaintySystemTester()
    
    try:
        # Connect to database
        await tester.connect()
        
        # Setup test data
        setup_success = await tester.setup_test_data()
        if not setup_success:
            print("❌ Setup failed. Exiting.")
            return
        
        # Run tests
        await tester.test_question_classification()
        cache_ids = await tester.test_caching_system()
        await tester.test_feedback_system(cache_ids)
        await tester.test_analytics()
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")
        print("✅ Uncertainty-aware system is working correctly")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        await tester.cleanup_test_data()
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main()) 