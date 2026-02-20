"""
Module containing API client functions for the VPN bot
"""
import asyncio
import logging
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)


async def make_request(method: str, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
    """
    Make HTTP request with retry logic and error handling
    """
    max_retries = 3
    retry_delay = 1  # seconds

    # Create a temporary session with SSL disabled for localtunnel requests
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    connector = aiohttp.TCPConnector(ssl=False)
    
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