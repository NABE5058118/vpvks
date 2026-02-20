"""
Module containing utility functions for the VPN bot
"""
import time
from typing import Dict, Any, Optional
import asyncio
import logging
import re
import aiohttp

logger = logging.getLogger(__name__)

# Global cache for frequently accessed data
cache_data: Dict[str, Any] = {}
CACHE_TIMEOUT = 300  # 5 minutes cache timeout


def is_cache_valid(cache_key: str) -> bool:
    """Check if cached data is still valid"""
    if cache_key not in cache_data:
        return False
    
    cached_at = cache_data[cache_key].get('cached_at', 0)
    ttl = cache_data[cache_key].get('ttl', CACHE_TIMEOUT)
    
    return time.time() - cached_at < ttl


def get_cached_data(cache_key: str) -> Optional[Any]:
    """Get data from cache if it's still valid"""
    if is_cache_valid(cache_key):
        return cache_data[cache_key]['data']
    return None


def set_cached_data(cache_key: str, data: Any, ttl: int = CACHE_TIMEOUT) -> None:
    """Store data in cache with TTL"""
    cache_data[cache_key] = {
        'data': data,
        'cached_at': time.time(),
        'ttl': ttl
    }