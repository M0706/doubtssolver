import logging
import logging.config
import sys
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'error_code'):
            log_entry['error_code'] = record.error_code
        if hasattr(record, 'execution_time'):
            log_entry['execution_time'] = record.execution_time
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)

def setup_logging(
    log_level: str = "INFO",
    log_file: str = "logs/app.log",
    enable_json_logging: bool = False
) -> None:
    """Setup logging configuration for the application"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path(log_file).parent
    log_dir.mkdir(exist_ok=True)
    
    # Choose formatter based on environment
    if enable_json_logging:
        formatter_class = "app.core.logging_config.JSONFormatter"
        format_string = ""  # JSONFormatter handles the format
    else:
        formatter_class = "logging.Formatter"
        format_string = (
            "%(asctime)s | %(levelname)-8s | %(name)-25s | "
            "%(funcName)-20s:%(lineno)-4d | %(message)s"
        )
    
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "class": formatter_class,
                "format": format_string,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {
                "format": "%(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "detailed",
                "filename": log_file,
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": "logs/error.log",
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
            }
        },
        "loggers": {
            "app": {
                "level": log_level,
                "handlers": ["console", "file", "error_file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["file"],
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "file"],
        }
    }
    
    logging.config.dictConfig(config)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(f"app.{name}")

# Performance logging utility
class PerformanceLogger:
    """Context manager for logging execution time"""
    
    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.extra = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.info(f"Starting {self.operation}", extra=self.extra)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.utcnow()
        execution_time = (end_time - self.start_time).total_seconds()
        
        extra = {**self.extra, "execution_time": execution_time}
        
        if exc_type is None:
            self.logger.info(
                f"Completed {self.operation} in {execution_time:.3f}s", 
                extra=extra
            )
        else:
            self.logger.error(
                f"Failed {self.operation} after {execution_time:.3f}s: {exc_val}", 
                extra=extra,
                exc_info=True
            )

# Error context utility
def log_error_context(logger: logging.Logger, error: Exception, **context) -> None:
    """Log error with additional context information"""
    logger.error(
        f"Error occurred: {type(error).__name__}: {str(error)}",
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            **context
        },
        exc_info=True
    ) 