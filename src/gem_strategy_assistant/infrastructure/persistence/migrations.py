import logging
from pathlib import Path
from typing import Optional

from gem_strategy_assistant.infrastructure.persistence.database import Database

logger = logging.getLogger(__name__)

CURRENT_VERSION = 2


class MigrationManager:
    def __init__(self, db: Database):
        self.db = db

    def get_schema_version(self) -> int:
        try:
            result = self.db.conn.execute(
                "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
            ).fetchone()
            return result[0] if result else 0
        except Exception:
            return 0

    def set_schema_version(self, version: int) -> None:
        self.db.conn.execute(
            """
            INSERT INTO schema_version (version, applied_at)
            VALUES (?, datetime('now'))
            """,
            (version,)
        )
        self.db.conn.commit()
        logger.info(f"Set schema version to {version}")

    def create_schema_version_table(self) -> None:
        self.db.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
        self.db.conn.commit()
        logger.info("Created schema_version table")

    def migrate_to_v1(self) -> None:
        logger.info("Applying migration to v1: Adding indexes")
        
        self.db.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_signals_date 
            ON signals(date DESC)
            """
        )
        
        self.db.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_signals_created_at 
            ON signals(created_at DESC)
            """
        )
        
        self.db.conn.commit()
        logger.info("Migration to v1 complete")

    def migrate_to_v2(self) -> None:
        """
        Migration to version 2: Add research cache table.
        
        Creates table for caching ETF research results.
        """
        logger.info("Applying migration to v2: Adding research_cache table")
        
        self.db.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                etf_name TEXT NOT NULL,
                research_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                UNIQUE(etf_name)
            )
            """
        )
        
        self.db.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_research_cache_etf 
            ON research_cache(etf_name, expires_at)
            """
        )
        
        self.db.conn.commit()
        logger.info("Migration to v2 complete")

    def run_migrations(self) -> None:
        logger.info("Checking for pending migrations")
        
        self.create_schema_version_table()
        
        current = self.get_schema_version()
        logger.info(f"Current schema version: {current}")
        logger.info(f"Target schema version: {CURRENT_VERSION}")
        
        if current >= CURRENT_VERSION:
            logger.info("Database schema is up to date")
            return
        
        migrations = {
            1: self.migrate_to_v1,
            2: self.migrate_to_v2,
        }
        
        for version in range(current + 1, CURRENT_VERSION + 1):
            if version in migrations:
                logger.info(f"Running migration to v{version}")
                migrations[version]()
                self.set_schema_version(version)
            else:
                logger.warning(f"No migration defined for v{version}")
        
        logger.info("All migrations complete")

    def reset_database(self) -> None:
        """
        Reset database to clean state.
        
        WARNING: This drops all tables and data!
        """
        logger.warning("Resetting database - all data will be lost!")
        
        tables = [
            "signals",
            "rankings",
            "research_cache",
            "schema_version",
        ]
        
        for table in tables:
            try:
                self.db.conn.execute(f"DROP TABLE IF EXISTS {table}")
                logger.info(f"Dropped table: {table}")
            except Exception as e:
                logger.error(f"Failed to drop {table}: {e}")
        
        self.db.conn.commit()
        
        self.db._create_tables()
        
        self.run_migrations()
        
        logger.info("Database reset complete")


def run_migrations(db_path: Optional[str] = None) -> None:
    """
    Convenience function to run migrations.
    
    Args:
        db_path: Path to database file (default: from settings)
    """
    if db_path is None:
        from gem_strategy_assistant.config import settings
        db_path = settings.db_path
    
    db = Database(db_path)
    manager = MigrationManager(db)
    manager.run_migrations()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
