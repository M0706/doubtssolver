"""
Custom exception classes for the Doubt Solver application.
All exceptions inherit from a base exception to allow for consistent error handling.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class DoubtsBaseSolverException(Exception):
    """Base exception for all application-specific errors"""
    
    def __init__(self, message: str, error_code: str = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


# Database Related Exceptions
class DatabaseError(DoubtsBaseSolverException):
    """Raised when database operations fail"""
    pass

class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""
    pass

class RecordNotFoundError(DatabaseError):
    """Raised when a requested record is not found"""
    pass

class RecordAlreadyExistsError(DatabaseError):
    """Raised when trying to create a record that already exists"""
    pass

class DatabaseTransactionError(DatabaseError):
    """Raised when database transaction fails"""
    pass


# Authentication & Authorization Exceptions
class AuthenticationError(DoubtsBaseSolverException):
    """Raised when authentication fails"""
    pass

class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid"""
    pass

class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired"""
    pass

class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid or malformed"""
    pass

class AuthorizationError(DoubtsBaseSolverException):
    """Raised when user is not authorized to perform an action"""
    pass

class InsufficientPermissionsError(AuthorizationError):
    """Raised when user lacks required permissions"""
    pass


# External Service Exceptions
class ExternalServiceError(DoubtsBaseSolverException):
    """Raised when external service calls fail"""
    pass

class AIServiceError(ExternalServiceError):
    """Raised when AI service integration fails"""
    pass

class AIServiceTimeoutError(AIServiceError):
    """Raised when AI service request times out"""
    pass

class AIServiceQuotaExceededError(AIServiceError):
    """Raised when AI service quota is exceeded"""
    pass

class NetworkError(ExternalServiceError):
    """Raised when network requests fail"""
    pass


# Validation & Input Exceptions
class ValidationError(DoubtsBaseSolverException):
    """Raised when input validation fails"""
    pass

class InvalidInputError(ValidationError):
    """Raised when input data is invalid"""
    pass

class MissingRequiredFieldError(ValidationError):
    """Raised when required fields are missing"""
    pass

class InvalidFormatError(ValidationError):
    """Raised when data format is invalid"""
    pass


# Business Logic Exceptions
class BusinessLogicError(DoubtsBaseSolverException):
    """Raised when business logic rules are violated"""
    pass

class QuestionProcessingError(BusinessLogicError):
    """Raised when question processing fails"""
    pass

class PromptGenerationError(BusinessLogicError):
    """Raised when prompt generation fails"""
    pass

class UserOperationError(BusinessLogicError):
    """Raised when user operations fail"""
    pass


# System & Configuration Exceptions
class ConfigurationError(DoubtsBaseSolverException):
    """Raised when configuration is invalid or missing"""
    pass

class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing"""
    pass

class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration values are invalid"""
    pass

class SystemError(DoubtsBaseSolverException):
    """Raised when system-level errors occur"""
    pass

class ResourceUnavailableError(SystemError):
    """Raised when required resources are unavailable"""
    pass


# HTTP Exception Mapping
def map_exception_to_http_exception(exc: DoubtsBaseSolverException) -> HTTPException:
    """Map custom exceptions to HTTP exceptions with appropriate status codes"""
    
    # Authentication/Authorization errors -> 401/403
    if isinstance(exc, (InvalidCredentialsError, TokenExpiredError, InvalidTokenError)):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details
            }
        )
    
    if isinstance(exc, (AuthorizationError, InsufficientPermissionsError)):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details
            }
        )
    
    # Not found errors -> 404
    if isinstance(exc, RecordNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details
            }
        )
    
    # Validation errors -> 400
    if isinstance(exc, ValidationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details
            }
        )
    
    # Conflict errors -> 409
    if isinstance(exc, RecordAlreadyExistsError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": exc.message,
                "error_code": exc.error_code,
                "details": exc.details
            }
        )
    
    # External service errors -> 502
    if isinstance(exc, ExternalServiceError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "External service temporarily unavailable",
                "error_code": exc.error_code,
                "details": {}
            }
        )
    
    # All other errors -> 500
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "message": "An internal server error occurred",
            "error_code": exc.error_code,
            "details": {}
        }
    ) 