"""
Feedback Routes for Questions and Cache Responses
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas import QuestionFeedback, CacheFeedback
from app.services.user_services import get_current_user
from app.services.cache_service import cache_service
from app.core.db import db
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger("feedback_routes")

@router.post("/questions/{question_id}/feedback")
async def submit_question_feedback(
    question_id: int,
    feedback: QuestionFeedback,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit feedback on a question response
    """
    
    user_id = current_user.get("user_id")
    
    try:
        logger.info(f"Submitting feedback for question {question_id}", extra={"user_id": user_id})
        
        # Store feedback in database
        await db.execute("""
            INSERT INTO question_feedback (
                question_id, user_id, rating, feedback_text, classification_feedback
            ) VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (question_id, user_id)
            DO UPDATE SET 
                rating = $3,
                feedback_text = $4,
                classification_feedback = $5
        """, question_id, user_id, feedback.rating, feedback.feedback_text, feedback.classification_feedback)
        
        logger.info("Question feedback submitted successfully")
        return {"message": "Feedback submitted successfully"}
        
    except Exception as e:
        logger.error(f"Error submitting question feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )


@router.post("/cache/{cache_id}/feedback")
async def submit_cache_feedback(
    cache_id: int,
    question_id: int,
    feedback: CacheFeedback,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit feedback on a cached response
    """
    
    user_id = current_user.get("user_id")
    
    try:
        logger.info(f"Submitting cache feedback for cache {cache_id}", extra={"user_id": user_id})
        
        # Use the cache service to handle feedback with auto-disable logic
        await cache_service.handle_feedback(
            cache_id, user_id, question_id, 
            feedback.feedback_type, feedback.feedback_text
        )
        
        logger.info("Cache feedback submitted successfully")
        return {"message": "Cache feedback submitted successfully"}
        
    except Exception as e:
        logger.error(f"Error submitting cache feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit cache feedback"
        )


@router.get("/questions/{question_id}/feedback")
async def get_question_feedback(
    question_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get feedback for a specific question (admin only for now)
    """
    
    try:
        feedback_data = await db.fetch("""
            SELECT 
                qf.rating, qf.feedback_text, qf.classification_feedback, qf.created_at,
                u.username
            FROM question_feedback qf
            JOIN users u ON qf.user_id = u.id
            WHERE qf.question_id = $1
            ORDER BY qf.created_at DESC
        """, question_id)
        
        return {
            "question_id": question_id,
            "feedback": [dict(row) for row in feedback_data]
        }
        
    except Exception as e:
        logger.error(f"Error getting question feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback"
        ) 