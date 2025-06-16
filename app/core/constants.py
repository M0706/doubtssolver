"""
Constants and configuration values used throughout the Doubt Solver application.
This file centralizes URLs, endpoints, and other constant values to improve maintainability.
"""

# =============================================================================
# External Service URLs
# =============================================================================

class ExternalServices:
    """External service URLs and endpoints"""
    
    # AI Service URLs
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    OPENROUTER_CHAT_COMPLETIONS = f"{OPENROUTER_BASE_URL}/chat/completions"
    
    # Gemini AI Service URLs
    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_GENERATE_CONTENT = f"{GEMINI_BASE_URL}/models/gemini-2.0-flash:generateContent"
    
    # Alternative AI Services (for future use)
    OPENAI_BASE_URL = "https://api.openai.com/v1"
    OPENAI_CHAT_COMPLETIONS = f"{OPENAI_BASE_URL}/chat/completions"
    
    # Other potential external services
    ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
    COHERE_BASE_URL = "https://api.cohere.ai/v1"


# =============================================================================
# API Endpoints
# =============================================================================

class APIEndpoints:
    """Internal API endpoint paths"""
    
    # Root endpoints
    ROOT = "/"
    HEALTH_CHECK = "/health"
    
    # Authentication endpoints
    AUTH_LOGIN = "/users/login"
    AUTH_REGISTER = "/users/register"
    AUTH_PROFILE = "/users/profile"
    
    # Q&A endpoints
    QA_ASK = "/ask"
    QA_HISTORY = "/history"
    
    # User management endpoints
    USERS_BASE = "/users"
    USERS_PROFILE = "/users/profile"
    USERS_UPDATE = "/users/update"
    USERS_DELETE = "/users/delete"


# =============================================================================
# Database Constants
# =============================================================================

class DatabaseConstants:
    """Database-related constants"""
    
    # Connection pool settings
    MIN_POOL_SIZE = 5
    MAX_POOL_SIZE = 20
    COMMAND_TIMEOUT = 60
    
    # Query limits
    MAX_QUESTION_HISTORY_LIMIT = 50
    DEFAULT_QUESTION_HISTORY_LIMIT = 20
    
    # Table names
    USERS_TABLE = "users"
    DOUBTS_TABLE = "doubts"
    SCHEMA_MIGRATIONS_TABLE = "schema_migrations"


# =============================================================================
# AI Service Constants
# =============================================================================

class AIServiceConstants:
    """AI service configuration constants"""
    
    # AI Service Providers
    PROVIDER_OPENROUTER = "openrouter"
    PROVIDER_GEMINI = "gemini"
    PROVIDER_OPENAI = "openai"
    
    # Default provider (can be changed via environment variable)
    DEFAULT_PROVIDER = PROVIDER_GEMINI  # Changed from openrouter to gemini
    
    # Model configurations by provider
    OPENROUTER_MODELS = {
        "default": "openai/gpt-3.5-turbo",
        "alternative": "openai/gpt-4"
    }
    
    GEMINI_MODELS = {
        "default": "gemini-2.0-flash",
        "alternative": "gemini-1.5-pro"
    }
    
    OPENAI_MODELS = {
        "default": "gpt-3.5-turbo",
        "alternative": "gpt-4"
    }
    
    # Request parameters
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 1500
    DEFAULT_TIMEOUT = 60.0
    DEFAULT_RETRIES = 2
    
    # Response limits
    MAX_RESPONSE_LENGTH = 4000
    MIN_RESPONSE_LENGTH = 10


# =============================================================================
# Security Constants
# =============================================================================

class SecurityConstants:
    """Security-related constants"""
    
    # Password requirements
    MIN_PASSWORD_LENGTH = 6
    MAX_PASSWORD_LENGTH = 128
    
    # JWT settings
    DEFAULT_ALGORITHM = "HS256"
    DEFAULT_ACCESS_TOKEN_EXPIRE_HOURS = 24
    
    # Rate limiting (for future implementation)
    MAX_REQUESTS_PER_MINUTE = 60
    MAX_REQUESTS_PER_HOUR = 1000


# =============================================================================
# Validation Constants
# =============================================================================

class ValidationConstants:
    """Input validation constants"""
    
    # Text length limits
    MIN_QUESTION_LENGTH = 10
    MAX_QUESTION_LENGTH = 2000
    MAX_USERNAME_LENGTH = 150
    MAX_EMAIL_LENGTH = 255
    MAX_SUBJECT_CATEGORY_LENGTH = 50
    MAX_QUESTION_TYPE_LENGTH = 50
    
    # Pagination limits
    MIN_PAGINATION_LIMIT = 1
    MAX_PAGINATION_LIMIT = 100
    DEFAULT_PAGINATION_LIMIT = 20
    MIN_PAGINATION_OFFSET = 0


# =============================================================================
# Logging Constants
# =============================================================================

class LoggingConstants:
    """Logging configuration constants"""
    
    # Log levels
    DEFAULT_LOG_LEVEL = "INFO"
    PRODUCTION_LOG_LEVEL = "WARNING"
    DEBUG_LOG_LEVEL = "DEBUG"
    
    # Log file settings
    DEFAULT_LOG_FILE = "logs/app.log"
    ERROR_LOG_FILE = "logs/error.log"
    MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # Log format settings
    ENABLE_JSON_LOGGING_PRODUCTION = True
    ENABLE_JSON_LOGGING_DEVELOPMENT = False


# =============================================================================
# HTTP Status Messages
# =============================================================================

class StatusMessages:
    """Standard status messages for API responses"""
    
    # Success messages
    SUCCESS = "Operation completed successfully"
    USER_CREATED = "User created successfully"
    LOGIN_SUCCESS = "Login successful"
    QUESTION_PROCESSED = "Question processed successfully"
    
    # Error messages
    INTERNAL_ERROR = "An internal server error occurred"
    VALIDATION_ERROR = "Invalid input provided"
    AUTHENTICATION_ERROR = "Authentication failed"
    AUTHORIZATION_ERROR = "Access denied"
    NOT_FOUND_ERROR = "Resource not found"
    
    # Service messages
    AI_SERVICE_UNAVAILABLE = "AI service is temporarily unavailable"
    DATABASE_ERROR = "Database operation failed"
    NETWORK_ERROR = "Network connection failed"


# =============================================================================
# Application Metadata
# =============================================================================

class AppMetadata:
    """Application metadata and version information"""
    
    NAME = "Doubt Solver Backend"
    DESCRIPTION = "AI-powered doubt solving platform with comprehensive error handling"
    VERSION = "1.0.0"
    
    # API documentation
    DOCS_URL = "/docs"
    REDOC_URL = "/redoc"
    
    # Health check response
    HEALTH_CHECK_RESPONSE = {
        "status": "healthy",
        "services": {
            "database": "unknown",
            "ai_service": "unknown"
        }
    }


# =============================================================================
# Environment Constants
# =============================================================================

class EnvironmentConstants:
    """Environment-specific constants"""
    
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"
    
    # Environment variable names
    ENV_LOG_LEVEL = "LOG_LEVEL"
    ENV_ENVIRONMENT = "ENVIRONMENT"
    ENV_DATABASE_URL = "DATABASE_URL"
    ENV_SECRET_KEY = "SECRET_KEY"
    ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
    ENV_GEMINI_API_KEY = "GEMINI_API_KEY"
    ENV_AI_PROVIDER = "AI_PROVIDER"
    ENV_JWT_ALGORITHM = "JWT_ALGORITHM"
    ENV_ACCESS_TOKEN_EXPIRE_HOURS = "ACCESS_TOKEN_EXPIRE_HOURS"


# =============================================================================
# Error Codes
# =============================================================================

class ErrorCodes:
    """Standardized error codes for the application"""
    
    # General errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # Authentication errors
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    
    # Database errors
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
    RECORD_ALREADY_EXISTS = "RECORD_ALREADY_EXISTS"
    
    # AI Service errors
    AI_SERVICE_UNAVAILABLE = "AI_SERVICE_UNAVAILABLE"
    AI_SERVICE_TIMEOUT = "AI_SERVICE_TIMEOUT"
    AI_SERVICE_QUOTA_EXCEEDED = "AI_SERVICE_QUOTA_EXCEEDED"
    
    # Business logic errors
    QUESTION_PROCESSING_ERROR = "QUESTION_PROCESSING_ERROR"
    PROMPT_GENERATION_ERROR = "PROMPT_GENERATION_ERROR"


# =============================================================================
# Utility Functions
# =============================================================================

def get_api_endpoint(endpoint_name: str) -> str:
    """Get full API endpoint URL"""
    return getattr(APIEndpoints, endpoint_name.upper(), "")

def get_external_service_url(service_name: str) -> str:
    """Get external service URL"""
    return getattr(ExternalServices, service_name.upper(), "")

def get_error_code(error_type: str) -> str:
    """Get standardized error code"""
    return getattr(ErrorCodes, error_type.upper(), ErrorCodes.INTERNAL_SERVER_ERROR)

def get_ai_service_url(provider: str = None) -> str:
    """Get the current AI service URL based on provider"""
    import os
    
    if provider is None:
        provider = os.getenv(EnvironmentConstants.ENV_AI_PROVIDER, AIServiceConstants.DEFAULT_PROVIDER)
    
    if provider == AIServiceConstants.PROVIDER_GEMINI:
        return ExternalServices.GEMINI_GENERATE_CONTENT
    elif provider == AIServiceConstants.PROVIDER_OPENROUTER:
        return ExternalServices.OPENROUTER_CHAT_COMPLETIONS
    elif provider == AIServiceConstants.PROVIDER_OPENAI:
        return ExternalServices.OPENAI_CHAT_COMPLETIONS
    else:
        # Default fallback
        return ExternalServices.GEMINI_GENERATE_CONTENT 