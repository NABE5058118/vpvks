
"""
Module containing session management functions for the VPN bot
"""
import logging
from typing import Optional
import aiohttp

logger = logging.getLogger(__name__)

# Create global aiohttp session for async HTTP requests
session: Optional[aiohttp.ClientSession] = None


async def get_session() -> aiohttp.ClientSession:
    """Get or create aiohttp session for async HTTP requests"""
    global session
    if session is None:
        # Create session with timeout and retry settings
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        session = aiohttp.ClientSession(timeout=timeout)
    return session


async def close_session():
    """Close aiohttp session when shutting down"""
    global session
    if session:
        await session.close()
        session = None