import os
import pathlib
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from app.core.db import db
from app.core.logging_config import setup_logging, get_logger
from app.core.exceptions import DoubtsBaseSolverException, map_exception_to_http_exception
from app.core.constants import APIEndpoints, AppMetadata, StatusMessages
from app.routes.users_router import router as users_router
from app.routes.qa_router import router as qa_router

# Load environment variables from .env file
load_dotenv()

# Setup logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    enable_json_logging=os.getenv("ENVIRONMENT", "development") == "production"
)

logger = get_logger("main")

app = FastAPI(
    title=AppMetadata.NAME,
    description=AppMetadata.DESCRIPTION,
    version=AppMetadata.VERSION
)


# Global exception handler for custom exceptions
@app.exception_handler(DoubtsBaseSolverException)
async def custom_exception_handler(request: Request, exc: DoubtsBaseSolverException):
    """Handle all custom application exceptions"""
    logger.error(
        f"Custom exception occurred: {exc.error_code}",
        extra={
            "error_code": exc.error_code,
            "error_message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None
        }
    )
    
    # Map to appropriate HTTP exception
    http_exc = map_exception_to_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail
    )


# Global exception handler for unexpected errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unexpected exceptions"""
    logger.critical(
        f"Unexpected error occurred: {type(exc).__name__}: {str(exc)}",
        extra={
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "message": "An unexpected internal server error occurred",
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": {}
        }
    )


# Include routers
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(qa_router, prefix="/qa", tags=["qa"])


@app.on_event("startup")
async def startup():
    """Application startup event"""
    try:
        logger.info("Starting Doubt Solver Backend application...")
        await db.connect()
        logger.info("🚀 Database connected and migrations applied successfully!")
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.critical(f"Failed to start application: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
async def shutdown():
    """Application shutdown event"""
    try:
        logger.info("Shutting down Doubt Solver Backend application...")
        await db.disconnect()
        logger.info("Database disconnected successfully")
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Error during application shutdown: {e}", exc_info=True)


@app.get(APIEndpoints.ROOT)
async def root():
    """Root endpoint - health check"""
    logger.info("Root endpoint accessed")
    return {
        "message": f"{AppMetadata.NAME} is running.",
        "status": "healthy",
        "version": AppMetadata.VERSION
    }


@app.get(APIEndpoints.HEALTH_CHECK)
async def health_check():
    """Detailed health check endpoint"""
    logger.info("Health check endpoint accessed")
    
    health_status = {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "services": {
            "database": "unknown",
            "ai_service": "unknown"
        }
    }
    
    try:
        # Check database connection
        pool = await db.get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        health_status["services"]["database"] = "healthy"
        logger.info("Database health check passed")
    except Exception as e:
        health_status["services"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
        logger.error(f"Database health check failed: {e}")
    
    return health_status
