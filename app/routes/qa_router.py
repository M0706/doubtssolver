from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.schemas import QuestionRequest, QuestionResponse, HistoryResponse, QuestionFeedback, CacheFeedback
from app.services.enhanced_qa import process_question_with_uncertainty
from app.services.qa_services import get_question_history
from app.services.cache_service import cache_service
from app.services.user_services import get_current_user
from app.core.logging_config import get_logger
from app.core.exceptions import (
    ValidationError, DatabaseError, AIServiceError, BusinessLogicError,
    AIServiceTimeoutError, AIServiceQuotaExceededError
)
from app.core.constants import APIEndpoints, ValidationConstants, StatusMessages
from typing import Optional
import traceback

router = APIRouter()
logger = get_logger("qa_router")

@router.post(APIEndpoints.QA_ASK, response_model=QuestionResponse)
async def ask_question(
    question_data: QuestionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Process a question using AI service with comprehensive error handling
    
    Args:
        question_data: Question request data
        current_user: Authenticated user information
        
    Returns:
        QuestionResponse: AI-generated answer
        
    Raises:
        HTTPException: For various error scenarios
    """
    
    user_id = current_user.get("user_id")
    
    try:
        # Input validation with detailed logging
        logger.info(
            "Processing question request",
            extra={
                "user_id": user_id,
                "question_length": len(question_data.question) if question_data.question else 0,
                "subject_category": question_data.subject_category,
                "question_type": question_data.question_type
            }
        )
        
        # Validate question content
        if not question_data.question or not question_data.question.strip():
            logger.warning("Empty question provided", extra={"user_id": user_id})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": StatusMessages.VALIDATION_ERROR,
                    "message": "Question cannot be empty",
                    "field": "question"
                }
            )
        
        # Check question length limits
        question_length = len(question_data.question.strip())
        if question_length < ValidationConstants.MIN_QUESTION_LENGTH:
            logger.warning(
                f"Question too short: {question_length} characters",
                extra={"user_id": user_id}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": StatusMessages.VALIDATION_ERROR,
                    "message": f"Question must be at least {ValidationConstants.MIN_QUESTION_LENGTH} characters long",
                    "field": "question",
                    "current_length": question_length,
                    "min_length": ValidationConstants.MIN_QUESTION_LENGTH
                }
            )
        
        if question_length > ValidationConstants.MAX_QUESTION_LENGTH:
            logger.warning(
                f"Question too long: {question_length} characters",
                extra={"user_id": user_id}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": StatusMessages.VALIDATION_ERROR,
                    "message": f"Question must not exceed {ValidationConstants.MAX_QUESTION_LENGTH} characters",
                    "field": "question",
                    "current_length": question_length,
                    "max_length": ValidationConstants.MAX_QUESTION_LENGTH
                }
            )
        
        # Process the question through enhanced service layer with uncertainty handling
        response = await process_question_with_uncertainty(
            question_text=question_data.question.strip(),
            user_id=user_id,
            user_category=question_data.subject_category,
            user_type=question_data.question_type
        )
        
        logger.info(
            f"Question processed successfully",
            extra={
                "user_id": user_id,
                "response_length": len(response.answer) if response.answer else 0
            }
        )
        
        return response
        
    except ValidationError as e:
        logger.warning(
            f"Validation error in question processing: {e.message}",
            extra={"user_id": user_id, "details": e.details}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": StatusMessages.VALIDATION_ERROR,
                "message": e.message,
                "details": e.details
            }
        )
    
    except AIServiceQuotaExceededError as e:
        logger.warning(
            f"AI service quota exceeded: {e.message}",
            extra={"user_id": user_id}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "AI_SERVICE_QUOTA_EXCEEDED",
                "message": "AI service quota exceeded. Please try again later.",
                "details": e.details
            }
        )
    
    except AIServiceTimeoutError as e:
        logger.error(
            f"AI service timeout: {e.message}",
            extra={"user_id": user_id}
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "error": "AI_SERVICE_TIMEOUT",
                "message": "AI service request timed out. Please try again.",
                "details": e.details
            }
        )
    
    except AIServiceError as e:
        logger.error(
            f"AI service error: {e.message}",
            extra={"user_id": user_id, "error_code": e.error_code}
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": e.error_code or "AI_SERVICE_ERROR",
                "message": StatusMessages.AI_SERVICE_UNAVAILABLE,
                "details": e.details
            }
        )
    
    except DatabaseError as e:
        logger.error(
            f"Database error in question processing: {e.message}",
            extra={"user_id": user_id, "error_code": e.error_code}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": e.error_code or "DATABASE_ERROR",
                "message": "Database operation failed. Please try again.",
                "details": e.details if e.details else {}
            }
        )
    
    except BusinessLogicError as e:
        logger.error(
            f"Business logic error: {e.message}",
            extra={"user_id": user_id}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "BUSINESS_LOGIC_ERROR",
                "message": e.message,
                "details": e.details
            }
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    
    except Exception as e:
        logger.error(
            f"Unexpected error in question processing: {str(e)}",
            extra={"user_id": user_id, "traceback": traceback.format_exc()}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": StatusMessages.INTERNAL_ERROR
            }
        )


@router.get(APIEndpoints.QA_HISTORY, response_model=HistoryResponse)
async def get_history(
    limit: int = Query(ValidationConstants.DEFAULT_PAGINATION_LIMIT, ge=ValidationConstants.MIN_PAGINATION_LIMIT, le=ValidationConstants.MAX_PAGINATION_LIMIT),
    offset: int = Query(0, ge=ValidationConstants.MIN_PAGINATION_OFFSET),
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's question history with comprehensive error handling
    
    Args:
        limit: Number of questions to return (default: 20, max: 50)
        offset: Number of questions to skip for pagination
        current_user: Authenticated user information
        
    Returns:
        HistoryResponse: List of previous questions and answers
        
    Raises:
        HTTPException: For various error scenarios
    """
    
    user_id = current_user.get("user_id")
    
    try:
        logger.info(
            "Fetching question history",
            extra={
                "user_id": user_id,
                "limit": limit,
                "offset": offset
            }
        )
        
        # Validate pagination parameters
        if limit > ValidationConstants.MAX_PAGINATION_LIMIT:
            logger.warning(
                f"Requested limit too high: {limit}",
                extra={"user_id": user_id}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": StatusMessages.VALIDATION_ERROR,
                    "message": f"Limit cannot exceed {ValidationConstants.MAX_PAGINATION_LIMIT}",
                    "field": "limit",
                    "max_value": ValidationConstants.MAX_PAGINATION_LIMIT
                }
            )
        
        # Get history from service layer
        history = await get_question_history(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        logger.info(
            f"Question history retrieved successfully",
            extra={
                "user_id": user_id,
                "questions_count": len(history.questions) if history and history.questions else 0
            }
        )
        
        return history
        
    except DatabaseError as e:
        logger.error(
            f"Database error in history retrieval: {e.message}",
            extra={"user_id": user_id, "error_code": e.error_code}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": e.error_code or "DATABASE_ERROR",
                "message": "Failed to retrieve question history. Please try again.",
                "details": e.details if e.details else {}
            }
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    
    except Exception as e:
        logger.error(
            f"Unexpected error in history retrieval: {str(e)}",
            extra={"user_id": user_id, "traceback": traceback.format_exc()}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "INTERNAL_SERVER_ERROR",
                "message": StatusMessages.INTERNAL_ERROR
            }
        )
