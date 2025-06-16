from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS, OPENAI_API_KEY, GEMINI_API_KEY, AI_PROVIDER
from app.core.logging_config import get_logger, PerformanceLogger
from app.core.exceptions import AIServiceError, AIServiceTimeoutError, AIServiceQuotaExceededError, NetworkError
from app.core.constants import ExternalServices, AIServiceConstants, get_ai_service_url
from app.services.external_request import ExternalRequest
import json
import os

logger = get_logger("ai_service")

class AIServiceProvider:
    """Factory class for different AI service providers"""
    
    @staticmethod
    def get_provider(provider_name: str = None):
        """Get the appropriate AI service provider"""
        if provider_name is None:
            provider_name = AI_PROVIDER
            
        if provider_name == AIServiceConstants.PROVIDER_GEMINI:
            return GeminiProvider()
        elif provider_name == AIServiceConstants.PROVIDER_OPENROUTER:
            return OpenRouterProvider()
        elif provider_name == AIServiceConstants.PROVIDER_OPENAI:
            return OpenAIProvider()
        else:
            # Default to Gemini
            return GeminiProvider()

class BaseAIProvider:
    """Base class for AI service providers"""
    
    def __init__(self):
        self.provider_name = "base"
        self.api_key = None
        self.base_url = None
        
    def validate_config(self):
        """Validate provider configuration"""
        if not self.api_key:
            raise AIServiceError(
                message=f"{self.provider_name} API key not configured",
                error_code="AI_SERVICE_NOT_CONFIGURED"
            )
    
    def prepare_headers(self):
        """Prepare headers for the request"""
        raise NotImplementedError
    
    def prepare_payload(self, prompt: str):
        """Prepare the request payload"""
        raise NotImplementedError
    
    def extract_response(self, response_json: dict):
        """Extract the AI response from the provider's response"""
        raise NotImplementedError
    
    def get_url(self):
        """Get the API URL for this provider"""
        return self.base_url

class GeminiProvider(BaseAIProvider):
    """Google Gemini AI service provider"""
    
    def __init__(self):
        super().__init__()
        self.provider_name = "Gemini"
        self.api_key = GEMINI_API_KEY
        self.base_url = ExternalServices.GEMINI_GENERATE_CONTENT
        
    def validate_config(self):
        super().validate_config()
        
    def prepare_headers(self):
        return {
            "Content-Type": "application/json"
        }
    
    def get_url(self):
        # Gemini uses API key as query parameter
        return f"{self.base_url}?key={self.api_key}"
    
    def prepare_payload(self, prompt: str):
        return {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }
    
    def extract_response(self, response_json: dict):
        try:
            # Extract content from Gemini response format
            candidates = response_json.get("candidates", [])
            if not candidates:
                raise AIServiceError(
                    message="No candidates in Gemini response",
                    error_code="AI_SERVICE_EMPTY_RESPONSE"
                )
            
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            
            if not parts:
                raise AIServiceError(
                    message="No parts in Gemini response",
                    error_code="AI_SERVICE_EMPTY_RESPONSE"
                )
            
            text = parts[0].get("text", "").strip()
            
            if not text:
                raise AIServiceError(
                    message="Empty text in Gemini response",
                    error_code="AI_SERVICE_EMPTY_RESPONSE"
                )
            
            return text
            
        except (IndexError, KeyError, TypeError) as e:
            raise AIServiceError(
                message="Failed to extract content from Gemini response",
                error_code="AI_SERVICE_PARSE_ERROR",
                details={"parse_error": str(e), "response_structure": str(response_json)[:200]}
            )

class OpenRouterProvider(BaseAIProvider):
    """OpenRouter AI service provider"""
    
    def __init__(self):
        super().__init__()
        self.provider_name = "OpenRouter"
        self.api_key = OPENAI_API_KEY  # OpenRouter uses the same key
        self.base_url = ExternalServices.OPENROUTER_CHAT_COMPLETIONS
        
    def prepare_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def prepare_payload(self, prompt: str):
        return {
            "model": AIServiceConstants.OPENROUTER_MODELS["default"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": AIServiceConstants.DEFAULT_TEMPERATURE,
            "max_tokens": AIServiceConstants.DEFAULT_MAX_TOKENS
        }
    
    def extract_response(self, response_json: dict):
        try:
            choices = response_json.get("choices", [])
            if not choices:
                raise AIServiceError(
                    message="No choices in OpenRouter response",
                    error_code="AI_SERVICE_EMPTY_RESPONSE"
                )
            
            message = choices[0].get("message", {})
            content = message.get("content", "").strip()
            
            if not content:
                raise AIServiceError(
                    message="Empty content in OpenRouter response",
                    error_code="AI_SERVICE_EMPTY_RESPONSE"
                )
            
            return content
            
        except (IndexError, KeyError, TypeError) as e:
            raise AIServiceError(
                message="Failed to extract content from OpenRouter response",
                error_code="AI_SERVICE_PARSE_ERROR",
                details={"parse_error": str(e)}
            )

class OpenAIProvider(BaseAIProvider):
    """OpenAI AI service provider"""
    
    def __init__(self):
        super().__init__()
        self.provider_name = "OpenAI"
        self.api_key = OPENAI_API_KEY
        self.base_url = ExternalServices.OPENAI_CHAT_COMPLETIONS
        
    def prepare_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def prepare_payload(self, prompt: str):
        return {
            "model": AIServiceConstants.OPENAI_MODELS["default"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": AIServiceConstants.DEFAULT_TEMPERATURE,
            "max_tokens": AIServiceConstants.DEFAULT_MAX_TOKENS
        }
    
    def extract_response(self, response_json: dict):
        try:
            choices = response_json.get("choices", [])
            if not choices:
                raise AIServiceError(
                    message="No choices in OpenAI response",
                    error_code="AI_SERVICE_EMPTY_RESPONSE"
                )
            
            message = choices[0].get("message", {})
            content = message.get("content", "").strip()
            
            if not content:
                raise AIServiceError(
                    message="Empty content in OpenAI response",
                    error_code="AI_SERVICE_EMPTY_RESPONSE"
                )
            
            return content
            
        except (IndexError, KeyError, TypeError) as e:
            raise AIServiceError(
                message="Failed to extract content from OpenAI response",
                error_code="AI_SERVICE_PARSE_ERROR",
                details={"parse_error": str(e)}
            )

async def get_ai_response(prompt: str, user_id: int = None, provider_name: str = None) -> str:
    """
    Get AI response for the given prompt with comprehensive error handling
    
    Args:
        prompt: The prompt to send to AI service
        user_id: Optional user ID for logging context
        provider_name: Optional AI provider name (gemini, openrouter, openai)
        
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
    
    # Get the AI provider
    provider = AIServiceProvider.get_provider(provider_name)
    
    try:
        # Validate provider configuration
        provider.validate_config()
        
        # Prepare request components
        headers = provider.prepare_headers()
        payload = provider.prepare_payload(prompt)
        url = provider.get_url()
        
        with PerformanceLogger(logger, f"{provider.provider_name} AI service request", user_id=user_id):
            logger.info(
                f"Sending request to {provider.provider_name} AI service",
                extra={
                    "user_id": user_id,
                    "prompt_length": len(prompt),
                    "provider": provider.provider_name,
                    "service_url": url.split('?')[0] if '?' in url else url  # Remove API key from logs
                }
            )
            
            response = await ExternalRequest.send(
                url=url,
                method="POST",
                headers=headers,
                json=payload,
                read_timeout=AIServiceConstants.DEFAULT_TIMEOUT,
                retries=AIServiceConstants.DEFAULT_RETRIES
            )
            
            if response is None:
                logger.error(f"{provider.provider_name} service returned no response", extra={"user_id": user_id})
                raise AIServiceError(
                    message=f"{provider.provider_name} service is currently unavailable",
                    error_code="AI_SERVICE_UNAVAILABLE",
                    details={"user_id": user_id, "provider": provider.provider_name}
                )
            
            # Check response status
            if response.status_code == 401:
                logger.error(f"{provider.provider_name} service authentication failed", extra={"user_id": user_id})
                raise AIServiceError(
                    message=f"{provider.provider_name} service authentication failed",
                    error_code="AI_SERVICE_AUTH_FAILED",
                    details={"status_code": response.status_code, "provider": provider.provider_name}
                )
            
            elif response.status_code == 429:
                logger.warning(f"{provider.provider_name} service quota exceeded", extra={"user_id": user_id})
                raise AIServiceQuotaExceededError(
                    message=f"{provider.provider_name} service quota exceeded, please try again later",
                    details={"status_code": response.status_code, "provider": provider.provider_name}
                )
            
            elif response.status_code >= 500:
                logger.error(
                    f"{provider.provider_name} service server error: {response.status_code}",
                    extra={"user_id": user_id, "status_code": response.status_code}
                )
                raise AIServiceError(
                    message=f"{provider.provider_name} service is experiencing server issues",
                    error_code="AI_SERVICE_SERVER_ERROR",
                    details={"status_code": response.status_code, "provider": provider.provider_name}
                )
            
            elif response.status_code != 200:
                logger.error(
                    f"{provider.provider_name} service returned unexpected status: {response.status_code}",
                    extra={"user_id": user_id, "status_code": response.status_code}
                )
                raise AIServiceError(
                    message=f"{provider.provider_name} service returned unexpected response",
                    error_code="AI_SERVICE_UNEXPECTED_RESPONSE",
                    details={"status_code": response.status_code, "provider": provider.provider_name}
                )
            
            try:
                response_json = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse {provider.provider_name} service response JSON: {e}", extra={"user_id": user_id})
                raise AIServiceError(
                    message=f"Invalid response format from {provider.provider_name} service",
                    error_code="AI_SERVICE_INVALID_RESPONSE",
                    details={"json_error": str(e), "provider": provider.provider_name}
                )
            
            # Extract AI response using provider-specific logic
            ai_content = provider.extract_response(response_json)
            
            logger.info(
                f"{provider.provider_name} response received successfully",
                extra={
                    "user_id": user_id,
                    "response_length": len(ai_content),
                    "provider": provider.provider_name
                }
            )
            
            return ai_content
                
    except AIServiceError:
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error in {provider.provider_name} AI service: {e}",
            extra={"user_id": user_id, "provider": provider.provider_name},
            exc_info=True
        )
        raise AIServiceError(
            message=f"An unexpected error occurred while communicating with {provider.provider_name} service",
            error_code="AI_SERVICE_UNEXPECTED_ERROR",
            details={"error": str(e), "user_id": user_id, "provider": provider.provider_name}
        ) 