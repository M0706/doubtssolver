from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS, OPENAI_API_KEY
from app.core.logging_config import get_logger, PerformanceLogger
from app.core.exceptions import AIServiceError, AIServiceTimeoutError, AIServiceQuotaExceededError, NetworkError
from app.core.constants import ExternalServices, AIServiceConstants
from app.services.external_request import ExternalRequest
import json

logger = get_logger("ai_service")

async def get_ai_response(prompt: str, user_id: int = None) -> str:
    """
    Get AI response for the given prompt with comprehensive error handling
    
    Args:
        prompt: The prompt to send to AI service
        user_id: Optional user ID for logging context
        
    Returns:
        str: AI response text
        
    Raises:
        AIServiceError: When AI service fails
        AIServiceTimeoutError: When request times out
        AIServiceQuotaExceededError: When quota is exceeded
    """
    
    if not prompt or not prompt.strip():
        logger.error("Empty or invalid prompt provided", extra={"user_id": user_id})
        raise AIServiceError(
            message="Prompt cannot be empty",
            details={"user_id": user_id}
        )
    
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key not configured")
        raise AIServiceError(
            message="AI service not properly configured",
            error_code="AI_SERVICE_NOT_CONFIGURED"
        )
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": AIServiceConstants.DEFAULT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": AIServiceConstants.DEFAULT_TEMPERATURE,
        "max_tokens": AIServiceConstants.DEFAULT_MAX_TOKENS
    }
    
    try:
        with PerformanceLogger(logger, "AI service request", user_id=user_id):
            logger.info(
                f"Sending request to AI service",
                extra={
                    "user_id": user_id,
                    "prompt_length": len(prompt),
                    "model": data["model"],
                    "service_url": ExternalServices.OPENROUTER_CHAT_COMPLETIONS
                }
            )
            
            response = await ExternalRequest.send(
                url=ExternalServices.OPENROUTER_CHAT_COMPLETIONS,
                method="POST",
                headers=headers,
                json=data,
                read_timeout=AIServiceConstants.DEFAULT_TIMEOUT,
                retries=AIServiceConstants.DEFAULT_RETRIES
            )
            
            if response is None:
                logger.error("AI service returned no response", extra={"user_id": user_id})
                raise AIServiceError(
                    message="AI service is currently unavailable",
                    error_code="AI_SERVICE_UNAVAILABLE",
                    details={"user_id": user_id}
                )
            
            # Check response status
            if response.status_code == 401:
                logger.error("AI service authentication failed", extra={"user_id": user_id})
                raise AIServiceError(
                    message="AI service authentication failed",
                    error_code="AI_SERVICE_AUTH_FAILED",
                    details={"status_code": response.status_code}
                )
            
            elif response.status_code == 429:
                logger.warning("AI service quota exceeded", extra={"user_id": user_id})
                raise AIServiceQuotaExceededError(
                    message="AI service quota exceeded, please try again later",
                    details={"status_code": response.status_code}
                )
            
            elif response.status_code >= 500:
                logger.error(
                    f"AI service server error: {response.status_code}",
                    extra={"user_id": user_id, "status_code": response.status_code}
                )
                raise AIServiceError(
                    message="AI service is experiencing server issues",
                    error_code="AI_SERVICE_SERVER_ERROR",
                    details={"status_code": response.status_code}
                )
            
            elif response.status_code != 200:
                logger.error(
                    f"AI service returned unexpected status: {response.status_code}",
                    extra={"user_id": user_id, "status_code": response.status_code}
                )
                raise AIServiceError(
                    message="AI service returned unexpected response",
                    error_code="AI_SERVICE_UNEXPECTED_RESPONSE",
                    details={"status_code": response.status_code}
                )
            
            try:
                response_json = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI service response JSON: {e}", extra={"user_id": user_id})
                raise AIServiceError(
                    message="Invalid response format from AI service",
                    error_code="AI_SERVICE_INVALID_RESPONSE",
                    details={"json_error": str(e)}
                )
            
            # Extract AI response
            try:
                ai_content = response_json.get("choices", [])[0].get("message", {}).get("content", "").strip()
                
                if not ai_content:
                    logger.warning("AI service returned empty content", extra={"user_id": user_id})
                    raise AIServiceError(
                        message="AI service returned empty response",
                        error_code="AI_SERVICE_EMPTY_RESPONSE",
                        details={"response_structure": str(response_json)[:200]}
                    )
                
                logger.info(
                    f"AI response received successfully",
                    extra={
                        "user_id": user_id,
                        "response_length": len(ai_content),
                        "model": data["model"]
                    }
                )
                
                return ai_content
                
            except (IndexError, KeyError, TypeError) as e:
                logger.error(
                    f"Failed to extract content from AI service response: {e}",
                    extra={"user_id": user_id, "response": str(response_json)[:200]}
                )
                raise AIServiceError(
                    message="Failed to parse AI service response structure",
                    error_code="AI_SERVICE_PARSE_ERROR",
                    details={"parse_error": str(e)}
                )
                
    except AIServiceError:
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in AI service: {e}",
            extra={"user_id": user_id},
            exc_info=True
        )
        raise AIServiceError(
            message="An unexpected error occurred while communicating with AI service",
            error_code="AI_SERVICE_UNEXPECTED_ERROR",
            details={"error": str(e), "user_id": user_id}
        ) 