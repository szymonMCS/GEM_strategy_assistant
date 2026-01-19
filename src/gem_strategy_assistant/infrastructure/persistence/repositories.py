import json
import logging
from datetime import datetime, timedelta
from typing import Optional
import sqlite3

from gem_strategy_assistant.domain import ETF, Signal, MomentumRanking
from .database import Database

logger = logging.getLogger(__name__)


class SignalRepository:
    """Repository for Signal entities."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def save(self, signal: Signal) -> int:
        """
        Save signal and return ID.
        
        Args:
            signal: Signal to save
            
        Returns:
            Database ID of saved signal
        """
        with self.db.connection() as conn:
            cursor = conn.execute("""
                INSERT INTO signals (
                    created_at, recommended_etf, previous_etf,
                    requires_rebalance, winner_momentum, ranking_json,
                    report, period_start, period_end
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.created_at.isoformat(),
                signal.recommended_etf.name,
                signal.previous_etf.name if signal.previous_etf else None,
                1 if signal.requires_rebalance else 0,
                signal.ranking.winner_momentum,
                json.dumps(signal.ranking.to_dict()),
                signal.report,
                signal.ranking.period_start.isoformat(),
                signal.ranking.period_end.isoformat()
            ))
            conn.commit()
            
            logger.info(f"Saved signal #{cursor.lastrowid}: {signal.recommended_etf.name}")
            return cursor.lastrowid
    
    def get_latest(self) -> Optional[Signal]:
        """Get most recent signal."""
        with self.db.connection() as conn:
            row = conn.execute("""
                SELECT * FROM signals ORDER BY created_at DESC LIMIT 1
            """).fetchone()
            
            if not row:
                return None
            
            return self._row_to_signal(row)
    
    def get_history(self, limit: int = 12) -> list[Signal]:
        """Get recent signals."""
        with self.db.connection() as conn:
            rows = conn.execute("""
                SELECT * FROM signals ORDER BY created_at DESC LIMIT ?
            """, (limit,)).fetchall()
            
            return [self._row_to_signal(row) for row in rows]
    
    def _row_to_signal(self, row: sqlite3.Row) -> Signal:
        """Convert DB row to Signal."""
        ranking_data = json.loads(row["ranking_json"])
        
        rankings = tuple(
            (ETF[name], momentum) 
            for name, momentum in ranking_data["rankings"]
        )
        
        ranking = MomentumRanking(
            rankings=rankings,
            period_start=datetime.fromisoformat(ranking_data["period_start"]),
            period_end=datetime.fromisoformat(ranking_data["period_end"]),
            calculated_at=datetime.fromisoformat(ranking_data["calculated_at"])
        )
        
        return Signal(
            recommended_etf=ETF[row["recommended_etf"]],
            ranking=ranking,
            previous_etf=ETF[row["previous_etf"]] if row["previous_etf"] else None,
            requires_rebalance=bool(row["requires_rebalance"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            report=row["report"]
        )
    

class ResearchCacheRepository:
    """Repository for research cache."""
    
    def __init__(self, db: Database, ttl_hours: int = 24):
        """
        Initialize repository.
        
        Args:
            db: Database instance
            ttl_hours: Time-to-live for cache entries in hours (default: 24)
        """
        self.db = db
        self.ttl_hours = ttl_hours
    
    def get(self, etf_name: str) -> Optional[dict]:
        """
        Get cached research data for ETF.
        
        Args:
            etf_name: ETF name
            
        Returns:
            Research data dict or None if not found/expired
        """
        with self.db.connection() as conn:
            row = conn.execute(
                """
                SELECT research_data, expires_at 
                FROM research_cache 
                WHERE etf_name = ? AND expires_at > datetime('now')
                """,
                (etf_name,)
            ).fetchone()
            
            if not row:
                logger.debug(f"Cache miss for {etf_name}")
                return None
            
            logger.info(f"Cache hit for {etf_name}")
            return json.loads(row["research_data"])
    
    def set(self, etf_name: str, research_data: dict) -> None:
        """
        Save research data to cache.
        
        Args:
            etf_name: ETF name
            research_data: Research data to cache
        """
        expires_at = datetime.now() + timedelta(hours=self.ttl_hours)
        
        with self.db.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO research_cache 
                (etf_name, research_data, created_at, expires_at)
                VALUES (?, ?, datetime('now'), ?)
                """,
                (etf_name, json.dumps(research_data), expires_at.isoformat())
            )
            conn.commit()
            
            logger.info(f"Cached research for {etf_name} (expires: {expires_at})")
    
    def delete(self, etf_name: str) -> None:
        """
        Delete cached research data.
        
        Args:
            etf_name: ETF name
        """
        with self.db.connection() as conn:
            conn.execute(
                "DELETE FROM research_cache WHERE etf_name = ?",
                (etf_name,)
            )
            conn.commit()
            logger.info(f"Deleted cache for {etf_name}")
    
    def clear_expired(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of entries removed
        """
        with self.db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM research_cache WHERE expires_at <= datetime('now')"
            )
            conn.commit()
            count = cursor.rowcount
            
            if count > 0:
                logger.info(f"Cleared {count} expired cache entries")
            
            return count
    
    def clear_all(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries removed
        """
        with self.db.connection() as conn:
            cursor = conn.execute("DELETE FROM research_cache")
            conn.commit()
            count = cursor.rowcount
            
            logger.info(f"Cleared all cache ({count} entries)")
            return count
