"""Unit tests for cache service."""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock

from src.services.cache_service import (
    InMemoryCache,
    CacheService,
    get_cache_service
)


class TestInMemoryCache:
    """Test in-memory cache backend."""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test setting and getting values."""
        cache = InMemoryCache()
        
        await cache.set("key1", "value1", ttl=60)
        result = await cache.get("key1")
        
        assert result == "value1"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self):
        """Test getting non-existent key."""
        cache = InMemoryCache()
        
        result = await cache.get("nonexistent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = InMemoryCache()
        
        await cache.set("key1", "value1", ttl=1)  # 1 second TTL
        
        # Should be available immediately
        result = await cache.get("key1")
        assert result == "value1"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        result = await cache.get("key1")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting keys."""
        cache = InMemoryCache()
        
        await cache.set("key1", "value1")
        await cache.delete("key1")
        
        result = await cache.get("key1")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self):
        """Test deleting non-existent key (should not error)."""
        cache = InMemoryCache()
        
        # Should not raise error
        await cache.delete("nonexistent")
    
    @pytest.mark.asyncio
    async def test_multiple_keys(self):
        """Test storing multiple keys."""
        cache = InMemoryCache()
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"


class TestCacheService:
    """Test cache service wrapper."""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test setting and getting values."""
        service = CacheService()
        
        await service.set("key1", "value1")
        result = await service.get("key1")
        
        assert result == "value1"
    
    @pytest.mark.asyncio
    async def test_custom_ttl(self):
        """Test setting custom TTL."""
        service = CacheService()
        
        await service.set("key1", "value1", ttl=1)
        
        # Should be available
        result = await service.get("key1")
        assert result == "value1"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # Should be expired
        result = await service.get("key1")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_default_ttl(self):
        """Test default TTL from settings."""
        service = CacheService()
        
        # Should use default TTL from settings
        await service.set("key1", "value1")
        result = await service.get("key1")
        assert result == "value1"
    
    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting keys."""
        service = CacheService()
        
        await service.set("key1", "value1")
        await service.delete("key1")
        
        result = await service.get("key1")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_custom_backend(self):
        """Test using custom backend."""
        mock_backend = Mock()
        mock_backend.get = AsyncMock(return_value="cached_value")
        mock_backend.set = AsyncMock()
        mock_backend.delete = AsyncMock()
        
        service = CacheService(backend=mock_backend)
        
        result = await service.get("key1")
        assert result == "cached_value"
        mock_backend.get.assert_called_once_with("key1")


class TestCacheServiceSingleton:
    """Test cache service singleton."""
    
    def test_get_cache_service_singleton(self):
        """Test that get_cache_service returns singleton."""
        service1 = get_cache_service()
        service2 = get_cache_service()
        
        assert service1 is service2



