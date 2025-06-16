"""
Feedback Routes
"""

from fastapi import APIRouter, Depends, HTTPException
from app.schemas import QuestionFeedback, CacheFeedback
from app.services.user_services import get_current_user
from app.services.cache_service import cache_service
from app.core.db import db
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger("feedback")

@router.post("/questions/{question_id}/feedback")
async def submit_question_feedback(
    question_id: int,
    feedback: QuestionFeedback,
    current_user: dict = Depends(get_current_user)
):
    """Submit feedback on a question response"""
    
    user_id = current_user.get("user_id")
    
    try:
        await db.execute("""
            INSERT INTO question_feedback (
                question_id, user_id, rating, feedback_text, classification_feedback
            ) VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (question_id, user_id)
            DO UPDATE SET rating = $3, feedback_text = $4, classification_feedback = $5
        """, question_id, user_id, feedback.rating, feedback.feedback_text, feedback.classification_feedback)
        
        return {"message": "Feedback submitted successfully"}
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")

@router.post("/cache/{cache_id}/feedback")
async def submit_cache_feedback(
    cache_id: int,
    question_id: int,
    feedback: CacheFeedback,
    current_user: dict = Depends(get_current_user)
):
    """Submit feedback on a cached response"""
    
    user_id = current_user.get("user_id")
    
    try:
        await cache_service.handle_feedback(
            cache_id, user_id, question_id, 
            feedback.feedback_type, feedback.feedback_text
        )
        
        return {"message": "Cache feedback submitted successfully"}
        
    except Exception as e:
        logger.error(f"Error submitting cache feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit cache feedback") 