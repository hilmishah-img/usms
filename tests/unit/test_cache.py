"""Unit tests for HybridCache service."""

import time
from datetime import datetime, timezone

import pytest


class TestCacheBasicOperations:
    """Tests for basic cache get/set operations."""

    def test_cache_set_and_get(self, test_cache):
        """Test setting and getting a value from cache."""
        test_cache.set("key1", "value1", ttl_memory=60, ttl_disk=300)
        result = test_cache.get("key1")

        assert result == "value1"

    def test_cache_get_nonexistent_key(self, test_cache):
        """Test getting a non-existent key returns None."""
        result = test_cache.get("nonexistent_key")
        assert result is None

    def test_cache_set_complex_objects(self, test_cache):
        """Test caching complex Python objects."""
        complex_data = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "number": 42,
            "string": "test",
        }

        test_cache.set("complex", complex_data, ttl_memory=60, ttl_disk=300)
        result = test_cache.get("complex")

        assert result == complex_data


class TestCacheTTL:
    """Tests for cache TTL (time-to-live) functionality."""

    def test_l1_cache_expires(self, test_cache):
        """Test that L1 cache entries expire after TTL."""
        test_cache.set("key1", "value1", ttl_memory=1, ttl_disk=300)

        # Should be available immediately
        assert test_cache.get("key1") == "value1"

        # Wait for L1 to expire
        time.sleep(2)

        # Should still be in L2 (disk) cache
        result = test_cache.get("key1")
        assert result == "value1"  # Retrieved from L2 and promoted to L1

    def test_both_caches_expire(self, test_cache):
        """Test that entries expire from both L1 and L2 after their TTLs."""
        test_cache.set("key1", "value1", ttl_memory=1, ttl_disk=2)

        # Wait for both to expire
        time.sleep(3)

        result = test_cache.get("key1")
        assert result is None


class TestCacheLayers:
    """Tests for L1 (memory) and L2 (disk) cache layers."""

    def test_l1_hit(self, test_cache):
        """Test L1 cache hit."""
        test_cache.set("key1", "value1", ttl_memory=60, ttl_disk=300)

        # First access
        result1 = test_cache.get("key1")

        # Second access should hit L1
        result2 = test_cache.get("key1")

        assert result1 == result2 == "value1"

        # Check statistics
        stats = test_cache.get_stats()
        assert stats["l1_hits"] >= 1

    def test_l2_promotion_to_l1(self, test_cache):
        """Test that L2 hits are promoted to L1."""
        test_cache.set("key1", "value1", ttl_memory=1, ttl_disk=300)

        # Wait for L1 to expire
        time.sleep(2)

        # Access should hit L2 and promote to L1
        result = test_cache.get("key1")
        assert result == "value1"

        # Next access should hit L1
        result2 = test_cache.get("key1")
        assert result2 == "value1"

        stats = test_cache.get_stats()
        assert stats["l2_hits"] >= 1

    def test_cache_miss(self, test_cache):
        """Test cache miss when key doesn't exist."""
        result = test_cache.get("nonexistent")
        assert result is None

        stats = test_cache.get_stats()
        assert stats["misses"] >= 1


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_invalidate_exact_key(self, test_cache):
        """Test invalidating a specific key."""
        test_cache.set("key1", "value1", ttl_memory=60, ttl_disk=300)
        test_cache.set("key2", "value2", ttl_memory=60, ttl_disk=300)

        # Invalidate only key1
        count = test_cache.invalidate(exact_key="key1")
        assert count >= 1

        # key1 should be gone
        assert test_cache.get("key1") is None

        # key2 should still exist
        assert test_cache.get("key2") == "value2"

    def test_invalidate_pattern(self, test_cache):
        """Test invalidating keys matching a pattern."""
        test_cache.set("meter:123:unit", "100", ttl_memory=60, ttl_disk=300)
        test_cache.set("meter:123:credit", "50", ttl_memory=60, ttl_disk=300)
        test_cache.set("meter:456:unit", "200", ttl_memory=60, ttl_disk=300)
        test_cache.set("account:123", "data", ttl_memory=60, ttl_disk=300)

        # Invalidate all meter:123:* keys
        count = test_cache.invalidate(pattern="meter:123:*")
        assert count >= 2

        # meter:123 keys should be gone
        assert test_cache.get("meter:123:unit") is None
        assert test_cache.get("meter:123:credit") is None

        # Other keys should still exist
        assert test_cache.get("meter:456:unit") == "200"
        assert test_cache.get("account:123") == "data"

    def test_clear_all(self, test_cache):
        """Test clearing all cache entries."""
        test_cache.set("key1", "value1", ttl_memory=60, ttl_disk=300)
        test_cache.set("key2", "value2", ttl_memory=60, ttl_disk=300)
        test_cache.set("key3", "value3", ttl_memory=60, ttl_disk=300)

        test_cache.clear()

        # All keys should be gone
        assert test_cache.get("key1") is None
        assert test_cache.get("key2") is None
        assert test_cache.get("key3") is None


class TestCacheStatistics:
    """Tests for cache statistics and monitoring."""

    def test_get_stats(self, test_cache):
        """Test getting cache statistics."""
        # Perform some operations
        test_cache.set("key1", "value1", ttl_memory=60, ttl_disk=300)
        test_cache.get("key1")  # Hit
        test_cache.get("nonexistent")  # Miss

        stats = test_cache.get_stats()

        assert isinstance(stats, dict)
        assert "hits" in stats
        assert "misses" in stats
        assert "l1_hits" in stats
        assert "l2_hits" in stats
        assert "l1_size" in stats
        assert "l2_size" in stats
        assert "total_requests" in stats
        assert "hit_rate_percent" in stats
        assert "evictions" in stats

    def test_hit_rate_calculation(self, test_cache):
        """Test hit rate percentage calculation."""
        # 3 hits
        test_cache.set("key1", "value1", ttl_memory=60, ttl_disk=300)
        test_cache.get("key1")
        test_cache.get("key1")
        test_cache.get("key1")

        # 1 miss
        test_cache.get("nonexistent")

        stats = test_cache.get_stats()

        # Hit rate should be 75% (3 hits / 4 total)
        assert stats["total_requests"] == 4
        assert stats["hits"] == 3
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 75.0

    def test_cache_sizes(self, test_cache):
        """Test cache size tracking."""
        # Add items
        for i in range(10):
            test_cache.set(f"key{i}", f"value{i}", ttl_memory=60, ttl_disk=300)

        stats = test_cache.get_stats()

        # L1 should have items
        assert stats["l1_size"] == 10

        # L2 should also have items
        assert stats["l2_size"] >= 10


class TestCacheCleanup:
    """Tests for cache cleanup operations."""

    def test_cleanup_removes_expired(self, test_cache):
        """Test that cleanup removes expired entries."""
        test_cache.set("key1", "value1", ttl_memory=1, ttl_disk=1)

        # Wait for expiration
        time.sleep(2)

        # Run cleanup
        test_cache.cleanup()

        # Entry should be gone
        assert test_cache.get("key1") is None

    def test_cleanup_preserves_valid_entries(self, test_cache):
        """Test that cleanup preserves valid (non-expired) entries."""
        test_cache.set("key1", "value1", ttl_memory=60, ttl_disk=300)

        test_cache.cleanup()

        # Entry should still exist
        assert test_cache.get("key1") == "value1"


class TestCacheEdgeCases:
    """Tests for cache edge cases and error handling."""

    def test_cache_none_value(self, test_cache):
        """Test caching None as a value."""
        test_cache.set("key1", None, ttl_memory=60, ttl_disk=300)

        # Should return None, but from cache (not a miss)
        result = test_cache.get("key1")
        assert result is None

    def test_cache_empty_string(self, test_cache):
        """Test caching empty string."""
        test_cache.set("key1", "", ttl_memory=60, ttl_disk=300)
        result = test_cache.get("key1")

        assert result == ""

    def test_cache_zero_value(self, test_cache):
        """Test caching zero values."""
        test_cache.set("key1", 0, ttl_memory=60, ttl_disk=300)
        result = test_cache.get("key1")

        assert result == 0

    def test_cache_large_object(self, test_cache):
        """Test caching large objects."""
        large_data = {"data": "x" * 10000}  # 10KB of data

        test_cache.set("large", large_data, ttl_memory=60, ttl_disk=300)
        result = test_cache.get("large")

        assert result == large_data

    def test_cache_with_datetime_objects(self, test_cache):
        """Test caching datetime objects."""
        now = datetime.now(timezone.utc)
        test_cache.set("datetime", now, ttl_memory=60, ttl_disk=300)
        result = test_cache.get("datetime")

        assert result == now
