"""Centralized rate limiter configuration."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Default rate limit applied unless overridden per-route.
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])
