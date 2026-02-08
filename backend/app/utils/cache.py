"""
Response Caching Utility
Simple in-memory cache for API responses to reduce duplicate AI calls
"""

import hashlib
from typing import Optional, Dict, Any


class ResponseCache:
    """Simple in-memory cache for API responses."""
    
    def __init__(self, maxsize: int = 100):
        """
        Initialize cache with maximum size.
        
        Args:
            maxsize: Maximum number of cached responses
        """
        self._cache: Dict[str, Any] = {}
        self._maxsize = maxsize
    
    def _hash_key(self, description: str) -> str:
        """
        Generate cache key from description using SHA-256 hash.
        
        Args:
            description: Text to hash
            
        Returns:
            16-character hex hash
        """
        return hashlib.sha256(description.encode()).hexdigest()[:16]
    
    def get(self, description: str) -> Optional[dict]:
        """
        Retrieve cached response for a given description.
        
        Args:
            description: Network description to look up
            
        Returns:
            Cached response dict or None if not found
        """
        key = self._hash_key(description)
        return self._cache.get(key)
    
    def set(self, description: str, response: dict):
        """
        Store response in cache using FIFO eviction policy.
        
        Args:
            description: Network description key
            response: Response data to cache
        """
        if len(self._cache) >= self._maxsize:
            # Remove oldest item (simple FIFO)
            self._cache.pop(next(iter(self._cache)))
        
        key = self._hash_key(description)
        self._cache[key] = response
    
    def clear(self):
        """Clear all cached responses."""
        self._cache.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


# Global cache instance
response_cache = ResponseCache(maxsize=100)
