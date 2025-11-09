"""Hybrid caching service with memory (L1) and disk (L2) layers."""

import hashlib
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any

from cachetools import TTLCache
from diskcache import Cache as DiskCache

from usms.api.config import get_settings

logger = logging.getLogger(__name__)


class HybridCache:
    """Two-tier hybrid cache with memory (L1) and disk (L2) layers.

    L1 (Memory): Fast, volatile, TTL-based using cachetools
    L2 (Disk): Slower, persistent, SQLite-backed using diskcache

    Attributes
    ----------
    l1 : TTLCache
        In-memory cache with automatic expiration
    l2 : DiskCache
        Disk-based persistent cache
    stats : dict
        Cache statistics (hits, misses, etc.)
    """

    def __init__(
        self,
        memory_size: int = 1000,
        disk_path: str | None = None,
        disk_size_limit: int = 1_073_741_824,  # 1 GB
    ):
        """Initialize hybrid cache.

        Parameters
        ----------
        memory_size : int, optional
            Maximum number of items in L1 cache, by default 1000
        disk_path : str | None, optional
            Path to disk cache directory, by default None (uses config)
        disk_size_limit : int, optional
            Maximum disk cache size in bytes, by default 1GB
        """
        # L1: In-memory cache (no TTL at initialization, set per item)
        self.l1 = {}  # We'll use a custom TTL dict
        self.l1_ttl = {}  # Store expiration times
        self.l1_max_size = memory_size

        # L2: Disk cache
        settings = get_settings()
        cache_path = disk_path or settings.CACHE_PATH  # Use config path
        cache_dir = Path(cache_path) / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        self.l2 = DiskCache(str(cache_dir), size_limit=disk_size_limit)

        # Statistics
        self.stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
        }

        logger.info(f"HybridCache initialized: L1={memory_size} items, L2={cache_dir}")

    def _is_expired(self, key: str) -> bool:
        """Check if L1 cache entry is expired.

        Parameters
        ----------
        key : str
            Cache key

        Returns
        -------
        bool
            True if expired or not found
        """
        if key not in self.l1_ttl:
            return True

        expiry = self.l1_ttl[key]
        if expiry is None:  # No expiration
            return False

        return datetime.now().timestamp() > expiry

    def _evict_expired(self) -> None:
        """Remove expired entries from L1 cache."""
        expired_keys = [k for k in list(self.l1.keys()) if self._is_expired(k)]
        for key in expired_keys:
            del self.l1[key]
            del self.l1_ttl[key]
            self.stats["evictions"] += 1

    def _evict_lru(self) -> None:
        """Evict least recently used item from L1 if at capacity."""
        if len(self.l1) >= self.l1_max_size:
            # Simple LRU: remove oldest by insertion order
            oldest_key = next(iter(self.l1))
            del self.l1[oldest_key]
            if oldest_key in self.l1_ttl:
                del self.l1_ttl[oldest_key]
            self.stats["evictions"] += 1

    def get(self, key: str) -> Any | None:
        """Get value from cache (L1 → L2 → None).

        Parameters
        ----------
        key : str
            Cache key

        Returns
        -------
        Any | None
            Cached value or None if miss
        """
        # Clean up expired entries periodically
        self._evict_expired()

        # Try L1 (memory)
        if key in self.l1 and not self._is_expired(key):
            self.stats["l1_hits"] += 1
            logger.debug(f"Cache L1 HIT: {key}")
            return self.l1[key]

        # Try L2 (disk)
        try:
            value = self.l2.get(key)
            if value is not None:
                self.stats["l2_hits"] += 1
                logger.debug(f"Cache L2 HIT: {key}")

                # Promote to L1
                self.l1[key] = value
                self.l1_ttl[key] = None  # No TTL for promoted items
                return value
        except Exception as e:
            logger.warning(f"L2 cache error for key {key}: {e}")

        # Miss
        self.stats["misses"] += 1
        logger.debug(f"Cache MISS: {key}")
        return None

    def set(
        self, key: str, value: Any, ttl_memory: int | None = None, ttl_disk: int | None = None
    ) -> None:
        """Set value in cache (both L1 and L2).

        Parameters
        ----------
        key : str
            Cache key
        value : Any
            Value to cache (must be pickle-able)
        ttl_memory : int | None, optional
            TTL for L1 in seconds, None for no expiration
        ttl_disk : int | None, optional
            TTL for L2 in seconds, None for no expiration
        """
        self.stats["sets"] += 1

        # Set in L1 (memory)
        self._evict_lru()  # Make space if needed
        self.l1[key] = value

        if ttl_memory is not None:
            self.l1_ttl[key] = datetime.now().timestamp() + ttl_memory
        else:
            self.l1_ttl[key] = None

        # Set in L2 (disk)
        try:
            if ttl_disk is not None:
                self.l2.set(key, value, expire=ttl_disk)
            else:
                self.l2.set(key, value)

            logger.debug(f"Cache SET: {key} (L1 TTL={ttl_memory}, L2 TTL={ttl_disk})")
        except Exception as e:
            logger.error(f"Failed to set L2 cache for key {key}: {e}")

    def invalidate(self, pattern: str | None = None, exact_key: str | None = None) -> int:
        """Invalidate cache entries.

        Parameters
        ----------
        pattern : str | None, optional
            Pattern to match keys (e.g., "meter:123*")
        exact_key : str | None, optional
            Exact key to invalidate

        Returns
        -------
        int
            Number of keys invalidated
        """
        count = 0

        if exact_key:
            # Invalidate exact key
            if exact_key in self.l1:
                del self.l1[exact_key]
                if exact_key in self.l1_ttl:
                    del self.l1_ttl[exact_key]
                count += 1

            try:
                if self.l2.get(exact_key) is not None:
                    self.l2.delete(exact_key)
                    count += 1
            except Exception:
                pass

            logger.info(f"Invalidated cache key: {exact_key}")
            return count

        if pattern:
            # Invalidate by pattern (simple prefix match)
            prefix = pattern.rstrip("*")

            # L1
            keys_to_delete = [k for k in self.l1.keys() if k.startswith(prefix)]
            for key in keys_to_delete:
                del self.l1[key]
                if key in self.l1_ttl:
                    del self.l1_ttl[key]
                count += 1

            # L2 (iterate all keys - expensive!)
            try:
                for key in list(self.l2):
                    if key.startswith(prefix):
                        self.l2.delete(key)
                        count += 1
            except Exception as e:
                logger.error(f"Error invalidating L2 cache by pattern: {e}")

            logger.info(f"Invalidated {count} cache keys matching pattern: {pattern}")

        return count

    def clear(self) -> None:
        """Clear all cache entries."""
        self.l1.clear()
        self.l1_ttl.clear()
        self.l2.clear()
        logger.info("Cache cleared (L1 and L2)")

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns
        -------
        dict
            Cache hit/miss statistics and sizes
        """
        total_requests = self.stats["l1_hits"] + self.stats["l2_hits"] + self.stats["misses"]
        hit_rate = (
            (self.stats["l1_hits"] + self.stats["l2_hits"]) / total_requests * 100
            if total_requests > 0
            else 0.0
        )

        return {
            **self.stats,
            "l1_size": len(self.l1),
            "l2_size": len(self.l2),
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
        }

    def cleanup(self) -> None:
        """Perform cache maintenance.

        - Remove expired L1 entries
        - Cull L2 cache if over size limit
        - Log statistics
        """
        # Clean expired L1 entries
        self._evict_expired()

        # Cull L2 if needed
        try:
            culled = self.l2.cull()
            if culled > 0:
                logger.info(f"Culled {culled} entries from L2 cache")
        except Exception as e:
            logger.error(f"Error culling L2 cache: {e}")

        # Log stats
        stats = self.get_stats()
        logger.info(f"Cache stats: {stats}")

    def close(self) -> None:
        """Close cache connections."""
        try:
            self.l2.close()
            logger.info("Cache closed")
        except Exception as e:
            logger.error(f"Error closing cache: {e}")


# Global cache instance
_cache_instance: HybridCache | None = None


def get_cache() -> HybridCache:
    """Get or create global cache instance.

    Returns
    -------
    HybridCache
        Global cache instance
    """
    global _cache_instance
    if _cache_instance is None:
        settings = get_settings()
        _cache_instance = HybridCache(
            memory_size=settings.CACHE_MEMORY_SIZE,
            disk_path=None,  # Uses default from config
            disk_size_limit=1_073_741_824,  # 1 GB
        )
    return _cache_instance
