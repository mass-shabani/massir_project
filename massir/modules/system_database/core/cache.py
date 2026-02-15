"""
Caching layer for database query results.
"""
import time
import hashlib
import asyncio
from typing import Any, Dict, Optional, List
from collections import OrderedDict
from dataclasses import dataclass, field

from ..core.exceptions import CacheError


@dataclass
class CacheEntry:
    """A single cache entry."""
    key: str
    value: Any
    created_at: float
    ttl: int  # Time to live in seconds
    hits: int = 0
    
    @property
    def expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl <= 0:
            return False  # Never expires
        return time.time() > (self.created_at + self.ttl)
    
    @property
    def age(self) -> float:
        """Age of the entry in seconds."""
        return time.time() - self.created_at


class QueryCache:
    """
    LRU cache for database query results.
    
    Features:
    - LRU eviction when max_size is reached
    - TTL-based expiration
    - Thread-safe operations
    - Cache statistics
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 300,
        cleanup_interval: int = 60
    ):
        """
        Initialize the query cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default time-to-live in seconds
            cleanup_interval: Interval for automatic cleanup in seconds
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        self._lock = asyncio.Lock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    def _generate_key(
        self,
        query: str,
        params: Optional[tuple] = None,
        db_name: str = "default"
    ) -> str:
        """Generate a unique cache key for a query."""
        content = f"{db_name}:{query}:{params or ()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def start(self):
        """Start the cleanup task."""
        if self._running:
            return
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Stop the cleanup task."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _cleanup_loop(self):
        """Periodic cleanup of expired entries."""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception:
                pass  # Ignore errors in cleanup
    
    async def get(
        self,
        query: str,
        params: Optional[tuple] = None,
        db_name: str = "default"
    ) -> Optional[Any]:
        """
        Get cached result for a query.
        
        Args:
            query: SQL query string
            params: Query parameters
            db_name: Database name
            
        Returns:
            Cached result or None if not found/expired
        """
        key = self._generate_key(query, params, db_name)
        
        async with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check expiration
            if entry.expired:
                del self._cache[key]
                self._misses += 1
                self._expirations += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.hits += 1
            self._hits += 1
            
            return entry.value
    
    async def set(
        self,
        query: str,
        value: Any,
        params: Optional[tuple] = None,
        db_name: str = "default",
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache a query result.
        
        Args:
            query: SQL query string
            value: Result to cache
            params: Query parameters
            db_name: Database name
            ttl: Time-to-live in seconds (uses default if None)
            
        Returns:
            True if cached successfully
        """
        key = self._generate_key(query, params, db_name)
        ttl = ttl if ttl is not None else self._default_ttl
        
        async with self._lock:
            # Evict if at max size
            while len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._evictions += 1
            
            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                ttl=ttl
            )
            
            # Add to cache (removes old entry if exists)
            if key in self._cache:
                del self._cache[key]
            self._cache[key] = entry
            
            return True
    
    async def delete(
        self,
        query: str,
        params: Optional[tuple] = None,
        db_name: str = "default"
    ) -> bool:
        """
        Delete a cached result.
        
        Args:
            query: SQL query string
            params: Query parameters
            db_name: Database name
            
        Returns:
            True if deleted, False if not found
        """
        key = self._generate_key(query, params, db_name)
        
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def clear(self):
        """Clear all cached entries."""
        async with self._lock:
            self._cache.clear()
    
    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        count = 0
        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.expired
            ]
            for key in expired_keys:
                del self._cache[key]
                count += 1
            self._expirations += count
        return count
    
    async def invalidate_table(self, table_name: str, db_name: str = "default"):
        """
        Invalidate all cache entries that might involve a table.
        
        This is a simple implementation that clears all cache entries
        when a table is modified. A more sophisticated implementation
        could parse queries to determine affected tables.
        
        Args:
            table_name: Table name
            db_name: Database name
        """
        # For simplicity, clear all cache when a table is modified
        # TODO: Implement smarter invalidation based on query parsing
        await self.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "evictions": self._evictions,
            "expirations": self._expirations,
            "default_ttl": self._default_ttl
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0


class CacheManager:
    """
    Manager for multiple database caches.
    
    Each database connection can have its own cache instance.
    """
    
    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        self._caches: Dict[str, QueryCache] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._enabled = True
    
    def get_cache(self, db_name: str) -> QueryCache:
        """Get or create cache for a database."""
        if db_name not in self._caches:
            self._caches[db_name] = QueryCache(
                max_size=self._max_size,
                default_ttl=self._default_ttl
            )
        return self._caches[db_name]
    
    async def start_all(self):
        """Start all cache cleanup tasks."""
        for cache in self._caches.values():
            await cache.start()
    
    async def stop_all(self):
        """Stop all cache cleanup tasks."""
        for cache in self._caches.values():
            await cache.stop()
    
    async def get(
        self,
        db_name: str,
        query: str,
        params: Optional[tuple] = None
    ) -> Optional[Any]:
        """Get cached result."""
        if not self._enabled:
            return None
        cache = self.get_cache(db_name)
        return await cache.get(query, params, db_name)
    
    async def set(
        self,
        db_name: str,
        query: str,
        value: Any,
        params: Optional[tuple] = None,
        ttl: Optional[int] = None
    ):
        """Cache a result."""
        if not self._enabled:
            return
        cache = self.get_cache(db_name)
        await cache.set(query, value, params, db_name, ttl)
    
    async def invalidate(self, db_name: str, table_name: str):
        """Invalidate cache for a table."""
        if not self._enabled:
            return
        cache = self.get_cache(db_name)
        await cache.invalidate_table(table_name, db_name)
    
    async def clear_all(self):
        """Clear all caches."""
        for cache in self._caches.values():
            await cache.clear()
    
    def enable(self):
        """Enable caching."""
        self._enabled = True
    
    def disable(self):
        """Disable caching."""
        self._enabled = False
    
    @property
    def enabled(self) -> bool:
        """Check if caching is enabled."""
        return self._enabled
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        return {
            name: cache.get_stats()
            for name, cache in self._caches.items()
        }
