"""Background job scheduler service using APScheduler."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from usms.api.services.cache import get_cache

logger = logging.getLogger(__name__)


class SchedulerService:
    """Background job scheduler for API maintenance tasks.

    Attributes
    ----------
    scheduler : AsyncIOScheduler
        APScheduler instance for async jobs
    cache : HybridCache
        Cache service for cleanup operations
    """

    def __init__(self):
        """Initialize scheduler service."""
        self.scheduler = AsyncIOScheduler()
        self.cache = get_cache()

    def start(self):
        """Start the scheduler and register all jobs."""
        # Job 1: Cache cleanup (every hour)
        self.scheduler.add_job(
            self.cleanup_cache,
            "interval",
            hours=1,
            id="cleanup_cache",
            name="Cache Cleanup",
            replace_existing=True,
        )

        # Job 2: Cache statistics logging (every 15 min)
        self.scheduler.add_job(
            self.log_cache_stats,
            "interval",
            minutes=15,
            id="log_cache_stats",
            name="Cache Statistics",
            replace_existing=True,
        )

        # Start scheduler
        self.scheduler.start()
        logger.info("🕐 Scheduler started with 2 background jobs")

    async def cleanup_cache(self):
        """Clean up expired cache entries and compact disk cache.

        This job runs hourly to:
        - Remove expired entries from L1 (memory)
        - Cull L2 (disk) cache if over size limit
        - Log cache statistics
        """
        logger.info("Running cache cleanup job...")
        try:
            self.cache.cleanup()
            logger.info("Cache cleanup completed successfully")
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}", exc_info=True)

    async def log_cache_stats(self):
        """Log cache statistics for monitoring.

        This job runs every 15 minutes to log:
        - Cache hit/miss rates
        - L1 and L2 sizes
        - Total requests served
        """
        try:
            stats = self.cache.get_stats()
            logger.info(
                f"📊 Cache stats: "
                f"Hit rate: {stats['hit_rate_percent']}%, "
                f"L1: {stats['l1_size']} items, "
                f"L2: {stats['l2_size']} items, "
                f"Total requests: {stats['total_requests']}"
            )
        except Exception as e:
            logger.error(f"Failed to log cache stats: {e}")

    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        self.scheduler.shutdown(wait=True)
        logger.info("👋 Scheduler shutdown complete")
