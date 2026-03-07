"""Rate Limiter configuration"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

limiter_storage = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=limiter_storage,
    strategy="fixed-window",
    default_limits=["100 per minute", "1000 per hour"]
)
