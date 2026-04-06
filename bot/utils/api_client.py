"""
Module containing API client functions for the VPN bot
"""
import asyncio
import logging
import ssl
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)

_ssl_context = None


def get_ssl_context() -> ssl.SSLContext:
    """Create and reuse SSL context with certificate verification"""
    global _ssl_context
    if _ssl_context is None:
        _ssl_context = ssl.create_default_context()
    return _ssl_context


def create_connector() -> aiohttp.TCPConnector:
    return aiohttp.TCPConnector(ssl=get_ssl_context())


def create_session(timeout: int = 30) -> aiohttp.ClientSession:
    return aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=timeout, connect=10),
        connector=create_connector()
    )


async def make_request(method: str, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
    """
    Make HTTP request with retry logic and error handling
    """
    max_retries = 3
    retry_delay = 1  # seconds

    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    connector = aiohttp.TCPConnector(ssl=get_ssl_context())

    for attempt in range(max_retries):
        client_session = None
        try:
            client_session = aiohttp.ClientSession(timeout=timeout, connector=connector)
            async with client_session:
                async with getattr(client_session, method.lower())(url, **kwargs) as response:
                    return response
        except aiohttp.ClientConnectorError as e:
            logger.warning(f"Connection error on attempt {attempt + 1}/{max_retries} for {url}: {e}")
            if client_session:
                await client_session.close()
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
            else:
                raise
        except aiohttp.ServerTimeoutError as e:
            logger.warning(f"Server timeout on attempt {attempt + 1}/{max_retries} for {url}: {e}")
            if client_session:
                await client_session.close()
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2 ** attempt))
            else:
                raise
        except aiohttp.ClientError as e:
            logger.warning(f"Client error on attempt {attempt + 1}/{max_retries} for {url}: {e}")
            if client_session:
                await client_session.close()
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2 ** attempt))
            else:
                raise
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}/{max_retries} for {url}: {e}")
            if client_session:
                await client_session.close()
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2 ** attempt))
            else:
                raise
