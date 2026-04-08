"""Shared helpers for repository modules."""

import sqlite3
from datetime import UTC, datetime
from typing import Any


def now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert a :class:`sqlite3.Row` to a plain dict, or return ``None``."""
    return dict(row) if row is not None else None
