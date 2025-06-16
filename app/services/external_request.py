import httpx
import asyncio
import logging
from typing import Optional, Dict, Any
from app.core.logging_config import get_logger
from app.core.exceptions import NetworkError, ExternalServiceError
import os

logger = get_logger("external_request")

class ExternalRequest:
    @classmethod
    async def send(
        cls,
        url: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Any = None,
        json: Any = None,
        read_timeout: float = 60.0,
        connect_timeout: float = 10.0,
        retries: int = 1,
        backoff_factor: float = 1.0,
    ) -> Optional[httpx.Response]:
        """
        Send HTTP request with comprehensive error handling and retry logic
        
        Args:
            url: Target URL
            method: HTTP method
            headers: Request headers
            params: Query parameters
            data: Request body data
            json: JSON request body
            read_timeout: Read timeout in seconds
            connect_timeout: Connection timeout in seconds
            retries: Number of retry attempts
            backoff_factor: Backoff multiplier for retries
            
        Returns:
            httpx.Response or None if all retries failed
            
        Raises:
            NetworkError: For network-related errors
            ExternalServiceError: For service-related errors
        """
        headers = headers or {}
        attempt = 0
        last_error = None
        
        # Sanitize URL for logging (remove sensitive parts)
        log_url = cls._sanitize_url_for_logging(url)
        
        logger.info(
            f"Starting external request",
            extra={
                "url": log_url,
                "method": method,
                "retries": retries,
                "read_timeout": read_timeout,
                "connect_timeout": connect_timeout
            }
        )
        
        while attempt < retries:
            try:
                timeout = httpx.Timeout(
                    connect=connect_timeout,
                    read=read_timeout,
                    write=read_timeout,
                    pool=connect_timeout
                )
                
                logger.debug(
                    f"Attempt {attempt + 1}/{retries} for {method} {log_url}",
                    extra={
                        "attempt": attempt + 1,
                        "max_retries": retries,
                        "url": log_url,
                        "method": method
                    }
                )
                
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                        data=data,
                        json=json,
                    )
                    
                    logger.info(
                        f"External request completed successfully",
                        extra={
                            "url": log_url,
                            "method": method,
                            "status_code": response.status_code,
                            "attempt": attempt + 1,
                            "response_size": len(response.content) if response.content else 0
                        }
                    )
                    
                    return response
                    
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    f"Timeout on attempt {attempt + 1} for {log_url}",
                    extra={
                        "url": log_url,
                        "method": method,
                        "attempt": attempt + 1,
                        "error_type": "timeout",
                        "timeout_read": read_timeout,
                        "timeout_connect": connect_timeout
                    }
                )
                
            except httpx.ConnectError as e:
                last_error = e
                logger.warning(
                    f"Connection error on attempt {attempt + 1} for {log_url}: {e}",
                    extra={
                        "url": log_url,
                        "method": method,
                        "attempt": attempt + 1,
                        "error_type": "connection",
                        "error_message": str(e)
                    }
                )
                
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(
                    f"HTTP error on attempt {attempt + 1} for {log_url}: {e.response.status_code}",
                    extra={
                        "url": log_url,
                        "method": method,
                        "attempt": attempt + 1,
                        "error_type": "http_status",
                        "status_code": e.response.status_code,
                        "response_text": e.response.text[:200] if e.response.text else ""
                    }
                )
                
            except httpx.RequestError as e:
                last_error = e
                logger.error(
                    f"Request error on attempt {attempt + 1} for {log_url}: {e}",
                    extra={
                        "url": log_url,
                        "method": method,
                        "attempt": attempt + 1,
                        "error_type": "request",
                        "error_message": str(e)
                    }
                )
                
            except Exception as e:
                last_error = e
                logger.error(
                    f"Unexpected error on attempt {attempt + 1} for {log_url}: {e}",
                    extra={
                        "url": log_url,
                        "method": method,
                        "attempt": attempt + 1,
                        "error_type": "unexpected",
                        "error_message": str(e)
                    },
                    exc_info=True
                )
            
            attempt += 1
            
            # Wait before retry (except on last attempt)
            if attempt < retries:
                wait_time = backoff_factor * attempt
                logger.info(
                    f"Waiting {wait_time}s before retry {attempt + 1}",
                    extra={
                        "url": log_url,
                        "wait_time": wait_time,
                        "next_attempt": attempt + 1,
                        "max_retries": retries
                    }
                )
                await asyncio.sleep(wait_time)
        
        # All retries failed
        logger.error(
            f"All {retries} attempts failed for {log_url}",
            extra={
                "url": log_url,
                "method": method,
                "total_attempts": retries,
                "final_error": str(last_error) if last_error else "Unknown"
            }
        )
        
        # Raise appropriate exception based on last error
        if isinstance(last_error, (httpx.TimeoutException, httpx.ConnectError)):
            raise NetworkError(
                message=f"Network error after {retries} attempts",
                details={
                    "url": log_url,
                    "method": method,
                    "attempts": retries,
                    "last_error": str(last_error)
                }
            )
        else:
            raise ExternalServiceError(
                message=f"External service error after {retries} attempts",
                details={
                    "url": log_url,
                    "method": method,
                    "attempts": retries,
                    "last_error": str(last_error) if last_error else "Unknown"
                }
            )
    
    @staticmethod
    def _sanitize_url_for_logging(url: str) -> str:
        """Remove sensitive information from URL for logging"""
        # Remove API keys and other sensitive query parameters
        if '?' in url:
            base_url, query_string = url.split('?', 1)
            # In a real implementation, you'd parse and filter query parameters
            return f"{base_url}?[FILTERED]"
        return url

os.makedirs("logs", exist_ok=True) 