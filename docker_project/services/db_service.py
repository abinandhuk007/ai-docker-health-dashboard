"""
db_service.py — PostgreSQL Query History Service

Stores and retrieves user query history and agent results.
Gracefully degrades (no-op) when DATABASE_URL is not configured.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Optional
from loguru import logger

try:
    from sqlalchemy import (
        create_engine, text, Column, Integer, String,
        DateTime, Text, Float, Boolean, MetaData, Table
    )
    from sqlalchemy.exc import SQLAlchemyError
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logger.warning("SQLAlchemy not installed — history disabled")


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS query_history (
    id          SERIAL PRIMARY KEY,
    query       TEXT NOT NULL,
    action      VARCHAR(50),
    intent_tag  VARCHAR(50),
    result_count INTEGER DEFAULT 0,
    retried     BOOLEAN DEFAULT FALSE,
    elapsed_ms  FLOAT,
    summary     TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);
"""


class DatabaseService:
    """
    Lightweight PostgreSQL service for storing query history.

    All public methods are safe to call even when the DB is unavailable —
    they log a warning and return a safe default.
    """

    def __init__(self) -> None:
        self._engine: Any = None
        self._available = False
        self._connect()

    def _connect(self) -> None:
        if not SQLALCHEMY_AVAILABLE:
            return

        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            logger.info("DatabaseService: DATABASE_URL not set — history disabled")
            return

        try:
            self._engine = create_engine(db_url, pool_pre_ping=True)
            with self._engine.connect() as conn:
                conn.execute(text(_CREATE_TABLE_SQL))
                conn.commit()
            self._available = True
            logger.info("DatabaseService: connected and schema ready")
        except Exception as exc:
            logger.warning(f"DatabaseService: cannot connect — {exc}")

    @property
    def is_available(self) -> bool:
        return self._available

    def save_query(
        self,
        query: str,
        action: str,
        intent_tag: str,
        result_count: int,
        retried: bool,
        elapsed_ms: float,
        summary: str,
    ) -> bool:
        """
        Persist a completed query to the history table.

        Returns:
            True on success, False on failure.
        """
        if not self._available:
            return False

        sql = text("""
            INSERT INTO query_history
                (query, action, intent_tag, result_count, retried, elapsed_ms, summary, created_at)
            VALUES
                (:query, :action, :intent_tag, :result_count, :retried, :elapsed_ms, :summary, :created_at)
        """)
        try:
            with self._engine.connect() as conn:
                conn.execute(sql, {
                    "query": query,
                    "action": action,
                    "intent_tag": intent_tag,
                    "result_count": result_count,
                    "retried": retried,
                    "elapsed_ms": elapsed_ms,
                    "summary": summary,
                    "created_at": datetime.utcnow(),
                })
                conn.commit()
            return True
        except Exception as exc:
            logger.warning(f"DatabaseService.save_query: {exc}")
            return False

    def get_recent_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Return the most recent `limit` queries from the history table.
        """
        if not self._available:
            return []

        sql = text("""
            SELECT id, query, action, result_count, retried, elapsed_ms, summary, created_at
            FROM query_history
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        try:
            with self._engine.connect() as conn:
                rows = conn.execute(sql, {"limit": limit}).fetchall()
            return [
                {
                    "id": r[0],
                    "query": r[1],
                    "action": r[2],
                    "result_count": r[3],
                    "retried": r[4],
                    "elapsed_ms": r[5],
                    "summary": r[6],
                    "created_at": str(r[7]),
                }
                for r in rows
            ]
        except Exception as exc:
            logger.warning(f"DatabaseService.get_recent_history: {exc}")
            return []

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate stats (total queries, most common actions, avg latency)."""
        if not self._available:
            return {}

        sql = text("""
            SELECT
                COUNT(*) as total,
                AVG(elapsed_ms) as avg_ms,
                SUM(CASE WHEN retried THEN 1 ELSE 0 END) as retried_count,
                AVG(result_count) as avg_results
            FROM query_history
        """)
        try:
            with self._engine.connect() as conn:
                row = conn.execute(sql).fetchone()
            if row:
                return {
                    "total_queries": int(row[0]),
                    "avg_latency_ms": round(float(row[1] or 0), 1),
                    "retried_count": int(row[2]),
                    "avg_results": round(float(row[3] or 0), 1),
                }
        except Exception as exc:
            logger.warning(f"DatabaseService.get_stats: {exc}")
        return {}
