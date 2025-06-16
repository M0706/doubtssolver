"""
Smart Question Cache Service with Safety Controls
Handles semantic similarity matching while preventing wrong answers
"""

import hashlib
import re
from typing import Optional, List, Dict
from dataclasses import dataclass
from app.core.db import db
from app.core.logging_config import get_logger

logger = get_logger("question_cache_service")

@dataclass
class CacheCandidate:
    id: int
    original_question_text: str
    cached_response: str
    category: str
    question_type: str
    similarity_threshold: float
    usage_count: int
    positive_feedback_count: int
    negative_feedback_count: int

class QuestionCacheService:
    
    async def get_cached_response(
        self, 
        question_text: str, 
        category: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Optional[Dict]:
        """
        Get cached response with safety checks
        """
        
        try:
            logger.info(f"Checking cache for question (user: {user_id})")
            
            # Find potential cache candidates
            candidates = await self._find_cache_candidates(question_text, category)
            
            if not candidates:
                logger.info("No cache candidates found")
                return None
            
            # Evaluate each candidate for safety
            for candidate in candidates:
                if self._is_safe_to_use_cache(question_text, candidate):
                    if self._passes_quality_checks(candidate):
                        await self._record_cache_usage(candidate.id)
                        
                        logger.info(f"Cache hit - returning cached response (cache_id: {candidate.id})")
                        
                        return {
                            "cache_id": candidate.id,
                            "response": candidate.cached_response,
                            "original_question": candidate.original_question_text,
                        }
            
            logger.info("No safe cache matches found")
            return None
            
        except Exception as e:
            logger.error(f"Error in cache lookup: {e}", exc_info=True)
            return None
    
    async def cache_response(
        self,
        question_text: str,
        response: str,
        category: Optional[str] = None,
        question_type: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Cache a new question-response pair
        """
        
        try:
            # Generate cache key and keywords
            pattern_hash = self._generate_pattern_hash(question_text)
            keywords = self._extract_keywords(question_text)
            
            # Determine safety settings
            safety_settings = self._get_safety_settings(question_text, category)
            
            logger.info(f"Caching new response (user: {user_id}, category: {category})")
            
            # Insert into cache
            cache_id = await db.fetchval("""
                INSERT INTO question_cache (
                    question_pattern_hash,
                    question_keywords,
                    original_question_text,
                    category,
                    question_type,
                    cached_response,
                    similarity_threshold,
                    requires_exact_numbers,
                    requires_exact_variables
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """,
                pattern_hash,
                keywords,
                question_text,
                category,
                question_type,
                response,
                safety_settings["similarity_threshold"],
                safety_settings["requires_exact_numbers"],
                safety_settings["requires_exact_variables"]
            )
            
            logger.info(f"Response cached successfully (cache_id: {cache_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error caching response: {e}", exc_info=True)
            return False
    
    async def handle_feedback(
        self,
        cache_id: int,
        user_id: int,
        question_id: int,
        feedback_type: str,
        feedback_text: Optional[str] = None
    ):
        """
        Handle user feedback on cached answers
        """
        
        try:
            logger.info(f"Recording cache feedback: {feedback_type} (cache_id: {cache_id})")
            
            # Record feedback
            await db.execute("""
                INSERT INTO cache_feedback (cache_id, user_id, question_id, feedback_type, feedback_text)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (cache_id, user_id, question_id) 
                DO UPDATE SET feedback_type = $4, feedback_text = $5
            """, cache_id, user_id, question_id, feedback_type, feedback_text)
            
            # Update counters
            if feedback_type == 'helpful':
                await db.execute("""
                    UPDATE question_cache 
                    SET positive_feedback_count = positive_feedback_count + 1
                    WHERE id = $1
                """, cache_id)
                
            elif feedback_type in ['wrong', 'irrelevant']:
                await db.execute("""
                    UPDATE question_cache 
                    SET negative_feedback_count = negative_feedback_count + 1
                    WHERE id = $1
                """, cache_id)
                
                # Check if we need to disable this cache entry
                await self._check_and_disable_cache(cache_id)
            
        except Exception as e:
            logger.error(f"Error handling cache feedback: {e}", exc_info=True)
    
    def _is_safe_to_use_cache(self, new_question: str, candidate: CacheCandidate) -> bool:
        """
        Safety checks to prevent wrong answers
        """
        
        # Check text similarity
        similarity = self._calculate_similarity(new_question, candidate.original_question_text)
        if similarity < candidate.similarity_threshold:
            return False
        
        # Extra checks for math questions
        if self._is_math_question(new_question):
            if not self._numbers_match(new_question, candidate.original_question_text):
                return False
        
        return True
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using word overlap
        """
        words1 = set(self._normalize_text(text1).split())
        words2 = set(self._normalize_text(text2).split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison
        """
        text = re.sub(r'\s+', ' ', text.lower().strip())
        text = re.sub(r'[^\w\s\+\-\*\/\=\(\)]', ' ', text)
        return text
    
    def _is_math_question(self, question: str) -> bool:
        """
        Detect if question is mathematical
        """
        math_indicators = ['equation', 'solve', 'calculate', '=', '+', '-', '*', '/', 'x', 'find x']
        question_lower = question.lower()
        return any(indicator in question_lower for indicator in math_indicators)
    
    def _numbers_match(self, text1: str, text2: str) -> bool:
        """
        Check if both texts contain the same numbers
        """
        numbers1 = set(re.findall(r'\d+(?:\.\d+)?', text1))
        numbers2 = set(re.findall(r'\d+(?:\.\d+)?', text2))
        return numbers1 == numbers2
    
    async def _find_cache_candidates(self, question_text: str, category: Optional[str]) -> List[CacheCandidate]:
        """
        Find potential cache candidates
        """
        keywords = self._extract_keywords(question_text)
        pattern_hash = self._generate_pattern_hash(question_text)
        
        rows = await db.fetch("""
            SELECT 
                id, original_question_text, cached_response, category, question_type,
                similarity_threshold, usage_count, positive_feedback_count, negative_feedback_count
            FROM question_cache 
            WHERE is_active = true
            AND (
                question_pattern_hash = $1  -- Exact pattern match
                OR question_keywords && $2  -- Keyword overlap
                OR ($3 IS NOT NULL AND category = $3)  -- Same category
            )
            ORDER BY 
                positive_feedback_count DESC,
                usage_count DESC
            LIMIT 10
        """, pattern_hash, keywords, category)
        
        candidates = []
        for row in rows:
            candidates.append(CacheCandidate(
                id=row['id'],
                original_question_text=row['original_question_text'],
                cached_response=row['cached_response'],
                category=row['category'],
                question_type=row['question_type'],
                similarity_threshold=row['similarity_threshold'],
                usage_count=row['usage_count'],
                positive_feedback_count=row['positive_feedback_count'],
                negative_feedback_count=row['negative_feedback_count']
            ))
        
        return candidates
    
    def _extract_keywords(self, question: str) -> List[str]:
        """
        Extract keywords for matching
        """
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = self._normalize_text(question).split()
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # Add numbers and variables as keywords
        numbers = re.findall(r'\d+(?:\.\d+)?', question)
        variables = re.findall(r'\b[a-z]\b', question.lower())
        
        return keywords + numbers + variables
    
    def _generate_pattern_hash(self, question: str) -> str:
        """
        Generate pattern hash for matching
        """
        normalized = self._normalize_text(question)
        # Replace numbers and variables with placeholders
        pattern = re.sub(r'\d+(?:\.\d+)?', 'NUM', normalized)
        pattern = re.sub(r'\b[a-z]\b', 'VAR', pattern)
        
        return hashlib.md5(pattern.encode()).hexdigest()[:16]
    
    def _get_safety_settings(self, question: str, category: Optional[str]) -> Dict:
        """
        Determine safety settings based on question type
        """
        settings = {
            "similarity_threshold": 0.85,
            "requires_exact_numbers": False,
            "requires_exact_variables": False
        }
        
        # Adjust based on category
        if category and any(word in category.lower() for word in ['math', 'quantitative']):
            settings.update({
                "similarity_threshold": 0.95,
                "requires_exact_numbers": True,
                "requires_exact_variables": True
            })
        
        # Adjust based on question content
        if self._is_math_question(question):
            settings.update({
                "similarity_threshold": 0.95,
                "requires_exact_numbers": True,
                "requires_exact_variables": True
            })
        
        return settings
    
    def _passes_quality_checks(self, candidate: CacheCandidate) -> bool:
        """
        Check if cache entry meets quality standards
        """
        # Too many negative feedbacks
        if candidate.negative_feedback_count >= 3:
            return False
        
        # More negative than positive feedback
        if candidate.negative_feedback_count > candidate.positive_feedback_count and candidate.usage_count > 5:
            return False
        
        return True
    
    async def _record_cache_usage(self, cache_id: int):
        """
        Record cache usage
        """
        await db.execute("""
            UPDATE question_cache 
            SET usage_count = usage_count + 1, last_used = NOW()
            WHERE id = $1
        """, cache_id)
    
    async def _check_and_disable_cache(self, cache_id: int):
        """
        Check if cache entry should be disabled
        """
        cache_entry = await db.fetchrow("""
            SELECT negative_feedback_count, positive_feedback_count
            FROM question_cache WHERE id = $1
        """, cache_id)
        
        if cache_entry and cache_entry['negative_feedback_count'] >= 3:
            await db.execute("""
                UPDATE question_cache 
                SET is_active = false, 
                    disabled_reason = 'Multiple negative feedbacks',
                    disabled_at = NOW()
                WHERE id = $1
            """, cache_id)
            
            logger.warning(f"Disabled cache entry {cache_id} due to negative feedback")

# Global instance
cache_service = QuestionCacheService() 