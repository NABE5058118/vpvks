"""
Module containing validation functions for the VPN bot
"""
import re
from typing import Any


def validate_user_id(user_id: Any) -> bool:
    """Validate user ID is a positive integer"""
    try:
        uid = int(user_id)
        return uid > 0
    except (ValueError, TypeError):
        return False


def validate_plan_id(plan_id: str) -> bool:
    """Validate plan ID contains only alphanumeric characters and hyphens"""
    return bool(re.match(r'^[a-zA-Z0-9\-]+$', plan_id))


def sanitize_input(input_str: str) -> str:
    """Sanitize input string to prevent injection attacks"""
    if not isinstance(input_str, str):
        return ""
    
    # Remove potentially dangerous characters
    sanitized = input_str.replace('<', '&lt;').replace('>', '&gt;')
    return sanitized