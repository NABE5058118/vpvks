"""
Configuration module for the VPN bot
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Get configuration values from environment
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')
MINI_APP_URL = os.getenv('MINI_APP_URL', 'https://example.com/miniapp')

# Admin user IDs (comma-separated list in environment variable)
ADMIN_IDS_STR = os.getenv('ADMIN_USER_IDS', '')
ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(',') if id.strip().isdigit()] if ADMIN_IDS_STR else []

def is_admin(user_id):
    """Check if user is admin"""
    return user_id in ADMIN_IDS

def check_env_vars():
    """Check if required environment variables are set"""
    errors = []
    
    if not BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN is not set")
    
    if not BACKEND_URL:
        errors.append("BACKEND_URL is not set")
    
    if errors:
        raise EnvironmentError("Missing required environment variables: " + ", ".join(errors))