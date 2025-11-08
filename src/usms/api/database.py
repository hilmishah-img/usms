"""Database management for API (SQLite for webhooks)."""

import aiosqlite
import logging
from pathlib import Path
from typing import AsyncGenerator

from usms.api.config import get_settings

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager for webhooks and API data.

    Attributes
    ----------
    db_path : str
        Path to SQLite database file
    """

    def __init__(self, db_path: str | None = None):
        """Initialize database manager.

        Parameters
        ----------
        db_path : str | None, optional
            Path to database file, by default None (uses config)
        """
        settings = get_settings()
        self.db_path = db_path or settings.WEBHOOK_DB_PATH

        # Ensure parent directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self) -> None:
        """Initialize database schema.

        Creates tables and indexes if they don't exist.
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Create webhooks table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS webhooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    meter_no TEXT NOT NULL,
                    url TEXT NOT NULL,
                    events TEXT NOT NULL,
                    secret TEXT,
                    active BOOLEAN DEFAULT 1,
                    failure_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_triggered TIMESTAMP,
                    last_success TIMESTAMP,
                    last_error TEXT
                )
            """)

            # Create indexes
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_webhooks_user ON webhooks(user_id)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_webhooks_meter ON webhooks(meter_no)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_webhooks_active ON webhooks(active)"
            )

            await db.commit()

        logger.info(f"Database initialized at {self.db_path}")

    async def get_connection(self) -> aiosqlite.Connection:
        """Get database connection.

        Returns
        -------
        aiosqlite.Connection
            Database connection

        Notes
        -----
        Caller is responsible for closing the connection.
        """
        return await aiosqlite.connect(self.db_path)

    async def execute(self, query: str, parameters: tuple = ()) -> aiosqlite.Cursor:
        """Execute a query and return cursor.

        Parameters
        ----------
        query : str
            SQL query
        parameters : tuple, optional
            Query parameters, by default ()

        Returns
        -------
        aiosqlite.Cursor
            Query cursor
        """
        async with await self.get_connection() as db:
            cursor = await db.execute(query, parameters)
            await db.commit()
            return cursor

    async def fetchone(self, query: str, parameters: tuple = ()) -> tuple | None:
        """Execute query and fetch one result.

        Parameters
        ----------
        query : str
            SQL query
        parameters : tuple, optional
            Query parameters, by default ()

        Returns
        -------
        tuple | None
            Query result or None
        """
        async with await self.get_connection() as db:
            cursor = await db.execute(query, parameters)
            return await cursor.fetchone()

    async def fetchall(self, query: str, parameters: tuple = ()) -> list[tuple]:
        """Execute query and fetch all results.

        Parameters
        ----------
        query : str
            SQL query
        parameters : tuple, optional
            Query parameters, by default ()

        Returns
        -------
        list[tuple]
            Query results
        """
        async with await self.get_connection() as db:
            cursor = await db.execute(query, parameters)
            return await cursor.fetchall()


# Global database instance
_db_instance: Database | None = None


def get_database() -> Database:
    """Get or create global database instance.

    Returns
    -------
    Database
        Global database instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
