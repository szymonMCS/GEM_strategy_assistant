import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)


class Database:
    
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        logger.info(f"Database initialized at {self.db_path}")
    
    def _init_schema(self) -> None:
        with self.connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    recommended_etf TEXT NOT NULL,
                    previous_etf TEXT,
                    requires_rebalance INTEGER NOT NULL,
                    winner_momentum REAL NOT NULL,
                    ranking_json TEXT NOT NULL,
                    report TEXT,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_signals_created_at
                ON signals(created_at DESC)
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    etf_name TEXT NOT NULL UNIQUE,
                    research_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_research_cache_etf
                ON research_cache(etf_name)
            """)

            conn.commit()
    
    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get database connection with automatic cleanup.
        
        Usage:
            with db.connection() as conn:
                conn.execute(...)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()