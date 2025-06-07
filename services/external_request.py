import httpx
import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

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
        headers = headers or {}
        attempt = 0
        while attempt < retries:
            try:
                timeout = httpx.Timeout(
                    connect=connect_timeout,
                    read=read_timeout,
                    write=read_timeout,
                    pool=connect_timeout
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
                    logger.info(f"External request to {url} succeeded with status {response.status_code}")
                    return response
            except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                logger.error(f"Timeout error on attempt {attempt+1} for {url}: {e}")
            except httpx.RequestError as e:
                logger.error(f"Request error on attempt {attempt+1} for {url}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt+1} for {url}: {e}")
            attempt += 1
            if attempt < retries:
                await asyncio.sleep(backoff_factor * attempt)
        logger.error(f"All {retries} attempts failed for {url}")
        return None 