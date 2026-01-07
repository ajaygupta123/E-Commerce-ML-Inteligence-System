"""Cache service with abstraction for Redis swap."""
from abc import ABC, abstractmethod
from typing import Optional, Any
import time
from collections import defaultdict

from ..core.config import settings


class CacheBackend(ABC):
    """Abstract cache backend - can swap InMemoryCache for RedisCache."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache with TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        pass


class InMemoryCache(CacheBackend):
    """
    In-memory cache implementation.
    
    Production note: Swap to RedisCache for:
    - Distributed caching across instances
    - Persistence across restarts
    - Better memory management
    """
    
    def __init__(self):
        self._cache: dict[str, tuple[Any, float]] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return None
        
        value, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None
        
        return value
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache with TTL."""
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        self._cache.pop(key, None)


class CacheService:
    """Cache service wrapper."""
    
    def __init__(self, backend: Optional[CacheBackend] = None):
        self.backend = backend or InMemoryCache()
        self.default_ttl = settings.cache_ttl
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return await self.backend.get(key)
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        await self.backend.set(key, value, ttl or self.default_ttl)
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        await self.backend.delete(key)


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get or create cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service




