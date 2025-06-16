from app.core.db import db
from app.core.logging_config import get_logger, PerformanceLogger
from app.core.exceptions import DatabaseError, ValidationError, QuestionProcessingError
from app.schemas import QuestionResponse, HistoryResponse, QuestionHistoryItem
from app.services.ai_service import get_ai_response
from datetime import datetime
import asyncpg

logger = get_logger("qa_services")

async def create_doubt_entry(
    user_id: int,
    question_text: str,
    full_prompt_sent: str,
    ai_response: str,
    subject_category: str = None,
    question_type: str = None  
):
    """
    Create a new doubt entry in the database with comprehensive error handling
    
    Args:
        user_id: ID of the user creating the doubt
        question_text: The original question text
        full_prompt_sent: The complete prompt sent to AI
        ai_response: The AI's response
        subject_category: Optional subject category
        question_type: Optional question type
        
    Returns:
        Database record of the created doubt entry
        
    Raises:
        ValidationError: When input validation fails
        DatabaseError: When database operation fails
        QuestionProcessingError: When question processing fails
    """
    
    # Input validation
    if not user_id or user_id <= 0:
        logger.error("Invalid user_id provided", extra={"user_id": user_id})
        raise ValidationError(
            message="Invalid user ID",
            details={"user_id": user_id}
        )
    
    if not question_text or not question_text.strip():
        logger.error("Empty question text provided", extra={"user_id": user_id})
        raise ValidationError(
            message="Question text cannot be empty",
            details={"user_id": user_id}
        )
    
    if not full_prompt_sent or not full_prompt_sent.strip():
        logger.error("Empty prompt provided", extra={"user_id": user_id})
        raise ValidationError(
            message="Prompt cannot be empty",
            details={"user_id": user_id}
        )
    
    if not ai_response or not ai_response.strip():
        logger.error("Empty AI response provided", extra={"user_id": user_id})
        raise ValidationError(
            message="AI response cannot be empty",
            details={"user_id": user_id}
        )
    
    # Sanitize inputs
    question_text = question_text.strip()
    full_prompt_sent = full_prompt_sent.strip()
    ai_response = ai_response.strip()
    
    logger.info(
        "Creating doubt entry",
        extra={
            "user_id": user_id,
            "question_length": len(question_text),
            "prompt_length": len(full_prompt_sent),
            "response_length": len(ai_response),
            "subject_category": subject_category,
            "question_type": question_type
        }
    )
    
    try:
        with PerformanceLogger(logger, "create_doubt_entry", user_id=user_id):
            pool = await db.get_pool()
            now = datetime.utcnow()
            
            query = """
                INSERT INTO doubts (user_id, question_text, full_prompt_sent, ai_response, timestamp, subject_category, question_type)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, user_id, question_text, full_prompt_sent, ai_response, timestamp, subject_category, question_type
            """
            
            async with pool.acquire() as conn:
                try:
                    row = await conn.fetchrow(
                        query,
                        user_id, question_text, full_prompt_sent, ai_response, now, subject_category, question_type
                    )
                    
                    if not row:
                        logger.error(
                            "Failed to create doubt entry - no row returned",
                            extra={"user_id": user_id}
                        )
                        raise QuestionProcessingError(
                            message="Failed to create doubt entry",
                            details={"user_id": user_id}
                        )
                    
                    logger.info(
                        "Doubt entry created successfully",
                        extra={
                            "user_id": user_id,
                            "doubt_id": row["id"],
                            "timestamp": row["timestamp"]
                        }
                    )
                    
                    return row
                    
                except asyncpg.ForeignKeyViolationError as e:
                    logger.error(
                        f"Foreign key violation - user does not exist: {e}",
                        extra={"user_id": user_id}
                    )
                    raise ValidationError(
                        message="User does not exist",
                        details={"user_id": user_id, "db_error": str(e)}
                    )
                    
                except asyncpg.PostgresError as e:
                    logger.error(
                        f"PostgreSQL error creating doubt entry: {e}",
                        extra={"user_id": user_id, "error_code": e.sqlstate},
                        exc_info=True
                    )
                    raise DatabaseError(
                        message="Database error while creating doubt entry",
                        details={
                            "user_id": user_id,
                            "postgres_error": str(e),
                            "error_code": e.sqlstate
                        }
                    )
                    
    except (ValidationError, QuestionProcessingError, DatabaseError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error creating doubt entry: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise QuestionProcessingError(
            message="Unexpected error while creating doubt entry",
            details={"user_id": user_id, "error": str(e)}
        )


async def get_user_doubts(user_id: int, limit: int = 50, offset: int = 0):
    """
    Retrieve doubts for a specific user with pagination
    
    Args:
        user_id: ID of the user
        limit: Maximum number of doubts to return
        offset: Number of doubts to skip
        
    Returns:
        List of doubt records
        
    Raises:
        ValidationError: When input validation fails
        DatabaseError: When database operation fails
    """
    
    # Input validation
    if not user_id or user_id <= 0:
        logger.error("Invalid user_id provided", extra={"user_id": user_id})
        raise ValidationError(
            message="Invalid user ID",
            details={"user_id": user_id}
        )
    
    if limit <= 0 or limit > 100:
        logger.error("Invalid limit provided", extra={"user_id": user_id, "limit": limit})
        raise ValidationError(
            message="Limit must be between 1 and 100",
            details={"user_id": user_id, "limit": limit}
        )
    
    if offset < 0:
        logger.error("Invalid offset provided", extra={"user_id": user_id, "offset": offset})
        raise ValidationError(
            message="Offset must be non-negative",
            details={"user_id": user_id, "offset": offset}
        )
    
    logger.info(
        "Retrieving user doubts",
        extra={
            "user_id": user_id,
            "limit": limit,
            "offset": offset
        }
    )
    
    try:
        with PerformanceLogger(logger, "get_user_doubts", user_id=user_id):
            pool = await db.get_pool()
            
            query = """
                SELECT id, user_id, question_text, full_prompt_sent, ai_response, 
                       timestamp, subject_category, question_type
                FROM doubts 
                WHERE user_id = $1 
                ORDER BY timestamp DESC 
                LIMIT $2 OFFSET $3
            """
            
            async with pool.acquire() as conn:
                try:
                    rows = await conn.fetch(query, user_id, limit, offset)
                    
                    logger.info(
                        f"Retrieved {len(rows)} doubts for user",
                        extra={
                            "user_id": user_id,
                            "doubt_count": len(rows),
                            "limit": limit,
                            "offset": offset
                        }
                    )
                    
                    return rows
                    
                except asyncpg.PostgresError as e:
                    logger.error(
                        f"PostgreSQL error retrieving user doubts: {e}",
                        extra={"user_id": user_id, "error_code": e.sqlstate},
                        exc_info=True
                    )
                    raise DatabaseError(
                        message="Database error while retrieving doubts",
                        details={
                            "user_id": user_id,
                            "postgres_error": str(e),
                            "error_code": e.sqlstate
                        }
                    )
                    
    except (ValidationError, DatabaseError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error retrieving user doubts: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise DatabaseError(
            message="Unexpected error while retrieving doubts",
            details={"user_id": user_id, "error": str(e)}
        )


async def process_question(
    question: str,
    subject_category: str = None,
    question_type: str = None,
    user_id: int = None
) -> QuestionResponse:
    """
    Process a question using AI service and save to database
    
    Args:
        question: The question to be processed
        subject_category: Optional subject category
        question_type: Optional question type
        user_id: ID of the user asking the question
        
    Returns:
        QuestionResponse: Processed question with AI answer
        
    Raises:
        ValidationError: When input validation fails
        QuestionProcessingError: When question processing fails
        DatabaseError: When database operation fails
    """
    
    if not question or not question.strip():
        logger.error("Empty question provided", extra={"user_id": user_id})
        raise ValidationError(
            message="Question cannot be empty",
            details={"user_id": user_id}
        )
    
    question = question.strip()
    
    logger.info(
        "Processing question",
        extra={
            "user_id": user_id,
            "question_length": len(question),
            "subject_category": subject_category,
            "question_type": question_type
        }
    )
    
    try:
        # Create AI prompt
        prompt = f"Question: {question}"
        if subject_category:
            prompt = f"Subject: {subject_category}\n{prompt}"
        
        # Get AI response
        ai_response = await get_ai_response(prompt, user_id)
        
        # Save to database
        doubt_record = await create_doubt_entry(
            user_id=user_id,
            question_text=question,
            full_prompt_sent=prompt,
            ai_response=ai_response,
            subject_category=subject_category,
            question_type=question_type
        )
        
        # Return formatted response
        return QuestionResponse(
            question_id=doubt_record["id"],
            question=question,
            answer=ai_response,
            subject_category=subject_category,
            question_type=question_type,
            timestamp=doubt_record["timestamp"]
        )
        
    except Exception as e:
        logger.error(
            f"Error processing question: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise


async def get_question_history(
    user_id: int,
    limit: int = 20,
    offset: int = 0
) -> HistoryResponse:
    """
    Get user's question history with pagination
    
    Args:
        user_id: ID of the user
        limit: Maximum number of questions to return
        offset: Number of questions to skip
        
    Returns:
        HistoryResponse: List of previous questions and answers
        
    Raises:
        ValidationError: When input validation fails
        DatabaseError: When database operation fails
    """
    
    logger.info(
        "Getting question history",
        extra={
            "user_id": user_id,
            "limit": limit,
            "offset": offset
        }
    )
    
    try:
        # Get user doubts
        doubt_records = await get_user_doubts(user_id, limit, offset)
        
        # Convert to history items
        questions = []
        for record in doubt_records:
            questions.append(QuestionHistoryItem(
                question_id=record["id"],
                question=record["question_text"],
                answer=record["ai_response"],
                subject_category=record["subject_category"],
                question_type=record["question_type"],
                timestamp=record["timestamp"]
            ))
        
        # Get total count for pagination info
        total_count = await get_user_doubt_count(user_id)
        
        return HistoryResponse(
            questions=questions,
            total_count=total_count,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(
            f"Error getting question history: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise


async def get_user_doubt_count(user_id: int) -> int:
    """
    Get total count of doubts for a user
    
    Args:
        user_id: ID of the user
        
    Returns:
        int: Total number of doubts
    """
    
    try:
        pool = await db.get_pool()
        
        query = "SELECT COUNT(*) FROM doubts WHERE user_id = $1"
        
        async with pool.acquire() as conn:
            count = await conn.fetchval(query, user_id)
            return count or 0
            
    except Exception as e:
        logger.error(
            f"Error getting user doubt count: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        return 0
