"""
Enhanced QA Service with Uncertainty Handling and Smart Caching
"""

import hashlib
import asyncio
import json
import re
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
    Process question with enhanced caching and intelligent invalidation
    """
    
    try:
        # Step 0: Check if user is re-asking the same question (invalidate cache if so)
        # cache_invalidated = await cache_service.check_and_invalidate_repeat_question(
        #     question_text, user_id, user_category
        # )
        
        # if cache_invalidated:
        #     logger.info(f"Cache invalidated due to repeat question from user {user_id}")
        
        # Step 1: Check cache first (only if not invalidated)
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
        
        # Step 3: Generate AI response (with context if cache was invalidated)
        # if cache_invalidated:
        #     # Add context to prompt that user was unsatisfied with previous answer
        #     ai_response = await generate_response_with_context(
        #         question_text, classification, user_id, "previous_answer_unsatisfactory"
        #     )
        # else:
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
    Attempt to classify question with AI-powered intelligent classification
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
    
    # Step 1: Use user-provided if available (highest confidence)
    if user_category and user_type:
        classification.update({
            "final_category": user_category,
            "final_type": user_type,
            "confidence": 0.9,  # High confidence in user input
            "method": "user"
        })
        return classification
    
    # Step 2: Try AI-powered classification (most accurate)
    try:
        ai_classification = await ai_classify_question(question_text, user_id)
        if ai_classification and ai_classification.get("confidence", 0) > 0.6:
            classification.update({
                "ai_category": ai_classification["category"],
                "ai_type": ai_classification["type"],
                "final_category": ai_classification["category"],
                "final_type": ai_classification["type"],
                "confidence": ai_classification["confidence"],
                "method": "ai"
            })
            return classification
    except Exception as e:
        logger.warning(f"AI classification failed: {e}")
    
    # Step 3: Fallback to keyword-based classification
    keyword_result = keyword_classify(question_text)
    if keyword_result:
        classification.update({
            "final_category": keyword_result["category"],
            "final_type": keyword_result["type"],
            "confidence": keyword_result["confidence"],
            "method": "keyword"
        })
        return classification
    
    # Step 4: Final fallback to Unknown
    classification.update({
        "final_category": "Unknown",
        "final_type": "Unknown",
        "confidence": 0.0,
        "method": "fallback"
    })
    
    return classification

async def ai_classify_question(question_text: str, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Use AI to intelligently classify the question with high accuracy
    """
    
    classification_prompt = f"""
You are an expert GMAT question classifier. Analyze the following question and classify it accurately.

QUESTION: {question_text}

CLASSIFICATION CATEGORIES:
1. **Quantitative Reasoning**
   - Problem Solving (algebra, arithmetic, geometry, word problems)
   - Data Sufficiency (analyzing if given information is sufficient)
   - Geometry (shapes, coordinates, measurements)
   - Statistics & Probability (data analysis, probability calculations)

2. **Verbal Reasoning**
   - Reading Comprehension (passage analysis, inference questions)
   - Critical Reasoning (argument analysis, assumptions, conclusions)
   - Sentence Correction (grammar, style, clarity)

3. **Analytical Writing**
   - Argument Analysis (critique reasoning and evidence)
   - Issue Analysis (develop position on complex issues)

4. **Integrated Reasoning**
   - Multi-Source Reasoning (synthesize information from multiple sources)
   - Table Analysis (interpret data in spreadsheet format)
   - Graphics Interpretation (analyze graphs, charts, diagrams)
   - Two-Part Analysis (solve complex problems with two components)

5. **General Academic**
   - Study Strategy (how to approach GMAT preparation)
   - Test-Taking Tips (timing, strategy, mindset)
   - Concept Explanation (fundamental concepts and theory)

INSTRUCTIONS:
1. Analyze the question content, structure, and requirements
2. Identify the primary subject area and specific question type
3. Consider what skills and knowledge are being tested
4. Assign a confidence score (0.0 to 1.0) based on how certain you are

RESPOND IN THIS EXACT JSON FORMAT:
{{
    "category": "[Primary Category]",
    "type": "[Specific Question Type]",
    "confidence": [0.0-1.0],
    "reasoning": "[Brief explanation of why this classification]"
}}

EXAMPLE CLASSIFICATIONS:
- "Solve for x: 2x + 5 = 15" → {{"category": "Quantitative Reasoning", "type": "Problem Solving", "confidence": 0.95}}
- "Is the data sufficient to determine..." → {{"category": "Quantitative Reasoning", "type": "Data Sufficiency", "confidence": 0.90}}
- "The passage suggests that..." → {{"category": "Verbal Reasoning", "type": "Reading Comprehension", "confidence": 0.85}}
- "Which of the following strengthens the argument?" → {{"category": "Verbal Reasoning", "type": "Critical Reasoning", "confidence": 0.90}}

Classify the question now:
"""
    
    try:
        ai_response = await get_ai_response(classification_prompt, user_id)
        
        # Parse the AI response (expecting JSON)
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*?\}', ai_response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            classification_data = json.loads(json_str)
            
            # Validate the response
            if all(key in classification_data for key in ["category", "type", "confidence"]):
                # Ensure confidence is a float between 0 and 1
                confidence = float(classification_data["confidence"])
                confidence = max(0.0, min(1.0, confidence))
                
                return {
                    "category": classification_data["category"],
                    "type": classification_data["type"],
                    "confidence": confidence,
                    "reasoning": classification_data.get("reasoning", "")
                }
        
        logger.warning(f"Invalid AI classification response: {ai_response}")
        return None
        
    except Exception as e:
        logger.error(f"Error in AI classification: {e}")
        return None

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

async def generate_response_with_context(
    question_text: str,
    classification: Dict[str, Any],
    user_id: int,
    context: str
) -> str:
    """
    Generate AI response with additional context about user's situation
    """
    
    # Create enhanced prompt based on context
    context_prompts = {
        "previous_answer_unsatisfactory": """
        IMPORTANT: The user has asked this question before, which suggests they were not satisfied 
        with the previous answer. Please provide a DIFFERENT approach or explanation:
        - Use a different teaching method
        - Provide more detailed steps
        - Include alternative solution approaches
        - Use simpler language or more examples
        """
    }
    
    additional_context = context_prompts.get(context, "")
    
    # Create appropriate prompt based on classification
    if classification["confidence"] > 0.5:
        prompt = f"""
        You are a GMAT tutor. This appears to be a {classification['final_type']} 
        question in {classification['final_category']}.
        
        {additional_context}
        
        Question: {question_text}
        
        Please provide a clear, step-by-step answer with a fresh perspective.
        """
    else:
        prompt = f"""
        You are a helpful GMAT tutor. Please analyze this question and provide 
        the best answer you can with clear reasoning.
        
        {additional_context}
        
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