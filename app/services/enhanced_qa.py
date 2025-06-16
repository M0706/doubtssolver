"""
Enhanced QA Service with Uncertainty Handling and Smart Caching
"""

import hashlib
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.db import db
from app.core.logging_config import get_logger
from app.core.exceptions import ValidationError, QuestionProcessingError
from app.schemas import QuestionResponse
from app.services.ai_service import get_ai_response
from app.services.cache_service import cache_service

logger = get_logger("enhanced_qa")

async def process_question_with_uncertainty(
    question_text: str,
    user_id: int,
    user_category: Optional[str] = None,
    user_type: Optional[str] = None
) -> QuestionResponse:
    """
    Process a question with uncertainty handling and smart caching
    """
    
    if not question_text or not question_text.strip():
        raise ValidationError("Question cannot be empty")
    
    question_text = question_text.strip()
    
    logger.info(f"Processing question for user {user_id}: {len(question_text)} chars")
    
    try:
        # Step 1: Check cache first
        cached_result = await cache_service.get_cached_response(
            question_text, user_category, user_id
        )
        
        if cached_result:
            question_id = await _store_cached_question(
                user_id, question_text, cached_result, user_category, user_type
            )
            
            return QuestionResponse(
                question_id=question_id,
                question=question_text,
                answer=cached_result["response"],
                subject_category=user_category,
                question_type=user_type,
                timestamp=datetime.utcnow()
            )
        
        # Step 2: Classify question with uncertainty handling
        classification = await attempt_classification(
            question_text, user_category, user_type, user_id
        )
        
        # Step 3: Generate AI response
        ai_response = await generate_response(question_text, classification, user_id)
        
        # Step 4: Store in database
        question_id = await store_question(
            user_id, question_text, classification, ai_response
        )
        
        # Step 5: Cache for future use
        await cache_service.cache_response(
            question_text, ai_response, 
            classification["final_category"], classification["final_type"],
            user_id
        )
        
        return QuestionResponse(
            question_id=question_id,
            question=question_text,
            answer=ai_response,
            subject_category=classification["final_category"],
            question_type=classification["final_type"],
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        raise QuestionProcessingError(f"Failed to process question: {str(e)}")

async def attempt_classification(
    question_text: str,
    user_category: Optional[str],
    user_type: Optional[str],
    user_id: int
) -> Dict[str, Any]:
    """
    Attempt to classify question with graceful fallbacks
    """
    
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
            "method": "user"
        })
        return classification
    
    # Try keyword-based classification
    keyword_result = keyword_classify(question_text)
    if keyword_result:
        classification.update({
            "final_category": keyword_result["category"],
            "final_type": keyword_result["type"],
            "confidence": keyword_result["confidence"],
            "method": "keyword"
        })
        return classification
    
    # Fallback to Unknown
    classification.update({
        "final_category": "Unknown",
        "final_type": "Unknown",
        "confidence": 0.0,
        "method": "fallback"
    })
    
    return classification

def keyword_classify(question_text: str) -> Optional[Dict[str, Any]]:
    """
    Simple keyword-based classification
    """
    
    text_lower = question_text.lower()
    
    # Math indicators
    math_keywords = ['equation', 'solve', 'calculate', 'x =', 'algebra', 'geometry']
    if any(keyword in text_lower for keyword in math_keywords):
        return {
            "category": "Quantitative Reasoning",
            "type": "Problem Solving",
            "confidence": 0.4
        }
    
    # Verbal indicators
    verbal_keywords = ['passage', 'author', 'paragraph', 'reading', 'comprehension']
    if any(keyword in text_lower for keyword in verbal_keywords):
        return {
            "category": "Verbal Reasoning", 
            "type": "Reading Comprehension",
            "confidence": 0.4
        }
    
    return None

async def generate_response(
    question_text: str,
    classification: Dict[str, Any],
    user_id: int
) -> str:
    """
    Generate AI response using classification info
    """
    
    # Create appropriate prompt based on classification
    if classification["confidence"] > 0.5:
        prompt = f"""
        You are a GMAT tutor. This appears to be a {classification['final_type']} 
        question in {classification['final_category']}.
        
        Question: {question_text}
        
        Please provide a clear, step-by-step answer.
        """
    else:
        prompt = f"""
        You are a helpful GMAT tutor. Please analyze this question and provide 
        the best answer you can with clear reasoning.
        
        Question: {question_text}
        """
    
    return await get_ai_response(prompt, user_id)

async def store_question(
    user_id: int,
    question_text: str,
    classification: Dict[str, Any],
    ai_response: str
) -> int:
    """
    Store question with uncertainty info
    """
    
    question_hash = hashlib.sha256(question_text.encode()).hexdigest()[:16]
    needs_review = classification["confidence"] < 0.5
    
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        question_id = await conn.fetchval("""
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
            user_id, question_text, question_hash,
            classification["user_category"], classification["user_type"],
            classification["ai_category"], classification["ai_type"],
            classification["final_category"], classification["final_type"],
            classification["confidence"], classification["method"],
            needs_review,
            ai_response, "Generated with uncertainty-aware system"
        )
    
    return question_id

async def _store_cached_question(
    user_id: int,
    question_text: str,
    cached_result: Dict,
    user_category: Optional[str],
    user_type: Optional[str]
) -> int:
    """
    Store cache hit for tracking
    """
    
    question_hash = hashlib.sha256(question_text.encode()).hexdigest()[:16]
    
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        question_id = await conn.fetchval("""
            INSERT INTO questions (
                user_id, question_text, question_hash,
                user_category, user_type,
                final_category, final_type,
                classification_confidence, classification_method,
                needs_manual_review,
                ai_response, full_prompt_sent,
                timestamp, status
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), 'cached'
            ) RETURNING id
        """,
            user_id, question_text, question_hash,
            user_category, user_type,
            user_category or "Unknown", user_type or "Unknown",
            1.0, "manual",
            False,
            cached_result["response"], "Served from cache"
        )
    
    return question_id 