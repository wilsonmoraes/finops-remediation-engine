"""The single SQLite access wrapper for the whole engine.

Every database call goes through here. Repos import these helpers; nothing else
in the codebase imports :mod:`sqlite3` directly. The connection enables foreign
keys (off by default in SQLite) and returns ``sqlite3.Row`` so callers index by
column name.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from app.config import get_settings


def _connect() -> sqlite3.Connection:
    settings = get_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection() -> Generator[sqlite3.Connection]:
    """Yield a connection, committing on success and rolling back on error.

    The commit-then-set-flag pattern lets the ``finally`` block roll back on any
    propagating exception without a broad ``except``: if control never reaches the
    commit, ``committed`` stays ``False`` and the original error propagates intact.
    """

    conn = _connect()
    committed = False
    try:
        yield conn
        conn.commit()
        committed = True
    finally:
        if not committed:
            conn.rollback()
        conn.close()


def execute(sql: str, params: dict[str, Any] | None = None) -> int:
    """Run a write statement and return the inserted row id (``lastrowid``)."""

    with connection() as conn:
        cur = conn.execute(sql, params or {})
        return int(cur.lastrowid or 0)


def query_all(sql: str, params: dict[str, Any] | None = None) -> list[sqlite3.Row]:
    """Run a read query and return all rows."""

    with connection() as conn:
        return conn.execute(sql, params or {}).fetchall()


def query_one(sql: str, params: dict[str, Any] | None = None) -> sqlite3.Row | None:
    """Run a read query and return the first row, or ``None``."""

    with connection() as conn:
        return conn.execute(sql, params or {}).fetchone()


def init_schema() -> None:
    """Apply the canonical schema from ``db/init_db.sql`` (idempotent)."""

    settings = get_settings()
    sql = settings.schema_path.read_text(encoding="utf-8")
    with connection() as conn:
        conn.executescript(sql)
