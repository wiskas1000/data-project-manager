"""Shared helpers for repository modules."""

from datetime import UTC, datetime


def now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()
