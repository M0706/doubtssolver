"""
Enhanced QA Service with Uncertainty Handling and Smart Caching
Replaces the old qa_services.py with modern uncertainty-aware processing
"""

import hashlib
import asyncio
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from app.core.db import db
from app.core.logging_config import get_logger, PerformanceLogger
from app.core.exceptions import DatabaseError, ValidationError, QuestionProcessingError
from app.schemas import QuestionResponse, HistoryResponse, QuestionHistoryItem
from app.services.ai_service import get_ai_response
from app.services.cache_service import cache_service
from app.utils.prompt_engineering import infer_subject_and_type, generate_gmat_prompt

logger = get_logger("enhanced_qa_service")

async def process_question_with_uncertainty(
    question_text: str,
    user_id: int,
    user_category: Optional[str] = None,
    user_type: Optional[str] = None,
    user_id_for_context: Optional[int] = None
) -> QuestionResponse:
    """
    Process a question with full uncertainty handling and smart caching
    
    This is the main entry point that replaces the old process_question function
    """
    
    # Step 1: Input validation
    if not question_text or not question_text.strip():
        logger.error("Empty question provided", extra={"user_id": user_id})
        raise ValidationError(
            message="Question cannot be empty",
            details={"user_id": user_id}
        )
    
    question_text = question_text.strip()
    
    logger.info(
        "Processing question with uncertainty handling",
        extra={
            "user_id": user_id,
            "question_length": len(question_text),
            "user_category": user_category,
            "user_type": user_type
        }
    )
    
    try:
        with PerformanceLogger(logger, "full_question_processing", user_id=user_id):
            
            # Step 2: Check cache first
            cached_result = await cache_service.get_cached_response(
                question_text, user_category, user_id
            )
            
            if cached_result:
                # Store cache hit in database for tracking
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
            
            # Step 3: No cache hit - process with AI
            logger.info("No cache hit, processing with AI", extra={"user_id": user_id})
            
            # Step 4: Attempt classification (with graceful failure handling)
            classification = await attempt_question_classification(
                question_text, user_category, user_type, user_id
            )
            
            # Step 5: Generate AI response using classification
            ai_response = await generate_ai_response_with_classification(
                question_text, classification, user_id
            )
            
            # Step 6: Store in database with all uncertainty info
            question_id = await store_question_with_uncertainty(
                user_id, question_text, classification, ai_response
            )
            
            # Step 7: Cache the response for future use
            await cache_service.cache_response(
                question_text, 
                ai_response, 
                classification["final_category"], 
                classification["final_type"],
                user_id
            )
            
            # Step 8: Return response
            return QuestionResponse(
                question_id=question_id,
                question=question_text,
                answer=ai_response,
                subject_category=classification["final_category"],
                question_type=classification["final_type"],
                timestamp=datetime.utcnow()
            )
            
    except Exception as e:
        logger.error(
            f"Error in enhanced question processing: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise QuestionProcessingError(
            message="Failed to process question",
            details={"user_id": user_id, "error": str(e)}
        )

async def attempt_question_classification(
    question_text: str,
    user_category: Optional[str],
    user_type: Optional[str],
    user_id: int
) -> Dict[str, Any]:
    """
    Attempt to classify question using multiple methods with graceful fallbacks
    """
    
    classification = {
        "user_category": user_category,
        "user_type": user_type,
        "ai_category": None,
        "ai_type": None,
        "final_category": None,
        "final_type": None,
        "confidence": 0.0,
        "method": "unknown"
    }
    
    logger.info(
        "Attempting question classification",
        extra={
            "user_id": user_id,
            "has_user_category": user_category is not None,
            "has_user_type": user_type is not None
        }
    )
    
    # Method 1: User-provided classification (if available)
    if user_category and user_type:
        classification.update({
            "final_category": user_category,
            "final_type": user_type,
            "confidence": 0.6,  # Medium confidence for user input
            "method": "user"
        })
        
        logger.info("Using user-provided classification", extra={"user_id": user_id})
        return classification
    
    # Method 2: AI classification (with timeout and error handling)
    try:
        logger.info("Attempting AI classification", extra={"user_id": user_id})
        
        ai_category, ai_type = await asyncio.wait_for(
            infer_subject_and_type(question_text),
            timeout=10.0  # Quick timeout for classification
        )
        
        if ai_category and ai_type and ai_category != "Unknown":
            classification.update({
                "ai_category": ai_category,
                "ai_type": ai_type,
                "final_category": ai_category,
                "final_type": ai_type,
                "confidence": 0.8,  # High confidence for successful AI classification
                "method": "ai"
            })
            
            logger.info(
                "AI classification successful",
                extra={
                    "user_id": user_id,
                    "ai_category": ai_category,
                    "ai_type": ai_type
                }
            )
            return classification
            
    except asyncio.TimeoutError:
        logger.warning("AI classification timed out", extra={"user_id": user_id})
    except Exception as e:
        logger.warning(f"AI classification failed: {e}", extra={"user_id": user_id})
    
    # Method 3: Keyword-based fallback
    keyword_result = keyword_classify_question(question_text)
    if keyword_result:
        classification.update({
            "final_category": keyword_result["category"],
            "final_type": keyword_result["type"],
            "confidence": keyword_result["confidence"],
            "method": "keyword"
        })
        
        logger.info(
            "Using keyword classification",
            extra={
                "user_id": user_id,
                "category": keyword_result["category"],
                "confidence": keyword_result["confidence"]
            }
        )
        return classification
    
    # Method 4: Complete fallback to "Unknown"
    classification.update({
        "final_category": "Unknown",
        "final_type": "Unknown",
        "confidence": 0.0,
        "method": "fallback"
    })
    
    logger.info("Using unknown classification fallback", extra={"user_id": user_id})
    return classification

def keyword_classify_question(question_text: str) -> Optional[Dict[str, Any]]:
    """
    Simple keyword-based classification as ultimate fallback
    """
    
    text_lower = question_text.lower()
    
    # Math/Quantitative indicators
    math_keywords = [
        'equation', 'solve', 'calculate', 'x =', 'find x', 'algebra', 'geometry',
        'formula', 'number', 'percentage', 'ratio', 'fraction', 'decimal'
    ]
    
    if any(keyword in text_lower for keyword in math_keywords):
        return {
            "category": "Quantitative Reasoning",
            "type": "Problem Solving",
            "confidence": 0.4
        }
    
    # Verbal/Reading indicators
    verbal_keywords = [
        'passage', 'author', 'paragraph', 'according to', 'text states',
        'reading', 'comprehension', 'grammar', 'sentence'
    ]
    
    if any(keyword in text_lower for keyword in verbal_keywords):
        return {
            "category": "Verbal Reasoning", 
            "type": "Reading Comprehension",
            "confidence": 0.4
        }
    
    return None

async def generate_ai_response_with_classification(
    question_text: str,
    classification: Dict[str, Any],
    user_id: int
) -> str:
    """
    Generate AI response using the classification information (or lack thereof)
    """
    
    try:
        # Create a doubt object for the prompt engineering function
        class DoubtObject:
            def __init__(self, question_text, category, question_type):
                self.question_text = question_text
                self.subject_category = category
                self.question_type = question_type
                self.options = None
        
        doubt = DoubtObject(
            question_text, 
            classification["final_category"], 
            classification["final_type"]
        )
        
        # Generate optimized prompt based on classification
        system_prompt, user_prompt, subject, qtype = await generate_gmat_prompt(doubt)
        
        # Combine prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        logger.info(
            "Generating AI response",
            extra={
                "user_id": user_id,
                "final_category": classification["final_category"],
                "final_type": classification["final_type"],
                "prompt_length": len(full_prompt)
            }
        )
        
        # Get AI response
        ai_response = await get_ai_response(full_prompt, user_id)
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error generating AI response: {e}", extra={"user_id": user_id}, exc_info=True)
        
        # Fallback to simple prompt
        simple_prompt = f"""
        You are a helpful GMAT tutor. Please answer this question clearly and step-by-step:
        
        {question_text}
        """
        
        return await get_ai_response(simple_prompt, user_id)

async def store_question_with_uncertainty(
    user_id: int,
    question_text: str,
    classification: Dict[str, Any],
    ai_response: str
) -> int:
    """
    Store question in database with all uncertainty tracking information
    """
    
    try:
        # Generate question hash for similarity matching
        question_hash = hashlib.sha256(question_text.encode()).hexdigest()[:16]
        
        # Determine if manual review is needed
        needs_review = classification["confidence"] < 0.5
        
        logger.info(
            "Storing question with uncertainty tracking",
            extra={
                "user_id": user_id,
                "confidence": classification["confidence"],
                "method": classification["method"],
                "needs_review": needs_review
            }
        )
        
        # Insert into questions table with full uncertainty info
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
        
        logger.info(
            "Question stored successfully",
            extra={
                "user_id": user_id,
                "question_id": question_id,
                "needs_review": needs_review
            }
        )
        
        return question_id
        
    except Exception as e:
        logger.error(
            f"Error storing question: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise DatabaseError(
            message="Failed to store question",
            details={"user_id": user_id, "error": str(e)}
        )

async def _store_cached_question(
    user_id: int,
    question_text: str,
    cached_result: Dict,
    user_category: Optional[str],
    user_type: Optional[str]
) -> int:
    """
    Store cache hit in database for tracking purposes
    """
    
    try:
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
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), 'manual'
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
        
    except Exception as e:
        logger.error(f"Error storing cached question: {e}", exc_info=True)
        raise

async def get_enhanced_question_history(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    include_confidence: bool = False
) -> HistoryResponse:
    """
    Get question history with enhanced uncertainty information
    """
    
    logger.info(
        "Getting enhanced question history",
        extra={
            "user_id": user_id,
            "limit": limit,
            "offset": offset,
            "include_confidence": include_confidence
        }
    )
    
    try:
        # Query questions with uncertainty info
        base_query = """
            SELECT 
                id, question_text, ai_response, 
                final_category, final_type,
                classification_confidence, classification_method,
                needs_manual_review, status, timestamp
            FROM questions 
            WHERE user_id = $1
            ORDER BY timestamp DESC
            LIMIT $2 OFFSET $3
        """
        
        pool = await db.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(base_query, user_id, limit, offset)
            
            questions = []
            for row in rows:
                question_item = QuestionHistoryItem(
                    question_id=row["id"],
                    question=row["question_text"],
                    answer=row["ai_response"],
                    subject_category=row["final_category"],
                    question_type=row["final_type"],
                    timestamp=row["timestamp"]
                )
                
                # Add confidence info if requested
                if include_confidence:
                    question_item.confidence = row["classification_confidence"]
                    question_item.method = row["classification_method"]
                    question_item.needs_review = row["needs_manual_review"]
                    question_item.status = row["status"]
                
                questions.append(question_item)
            
            # Get total count
            total_count = await conn.fetchval(
                "SELECT COUNT(*) FROM questions WHERE user_id = $1",
                user_id
            )
        
        return HistoryResponse(
            questions=questions,
            total_count=total_count or 0,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(
            f"Error getting enhanced question history: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise DatabaseError(
            message="Failed to retrieve question history",
            details={"user_id": user_id, "error": str(e)}
        )

async def submit_question_feedback(
    question_id: int,
    user_id: int,
    rating: int,
    feedback_text: Optional[str] = None,
    classification_feedback: Optional[Dict] = None
) -> bool:
    """
    Submit feedback on a question response
    """
    
    try:
        logger.info(
            "Submitting question feedback",
            extra={
                "question_id": question_id,
                "user_id": user_id,
                "rating": rating
            }
        )
        
        pool = await db.get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO question_feedback (
                    question_id, user_id, rating, feedback_text, classification_feedback
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (question_id, user_id)
                DO UPDATE SET 
                    rating = $3,
                    feedback_text = $4,
                    classification_feedback = $5
            """, question_id, user_id, rating, feedback_text, classification_feedback)
        
        logger.info("Question feedback submitted successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error submitting question feedback: {e}", exc_info=True)
        return False

# Backward compatibility function
async def process_question(
    question: str,
    subject_category: str = None,
    question_type: str = None,
    user_id: int = None
) -> QuestionResponse:
    """
    Backward compatibility wrapper for the old process_question function
    """
    return await process_question_with_uncertainty(
        question_text=question,
        user_id=user_id,
        user_category=subject_category,
        user_type=question_type
    ) 