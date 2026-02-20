import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Add additional logging for debugging
logging.getLogger('telegram').setLevel(logging.DEBUG)
logging.getLogger('httpx').setLevel(logging.DEBUG)

# Check required environment variables
try:
    from config import check_env_vars
    check_env_vars()
except EnvironmentError as e:
    logger.error(str(e))
    exit(1)

# Import configuration values
from config import BOT_TOKEN, BACKEND_URL, is_admin, MINI_APP_URL