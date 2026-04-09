"""ChangeLogEntry dataclass."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class ChangeLogEntry:
    """A field-level change record in the audit trail."""

    id: str
    entity_type: str
    entity_id: str
    field_name: str
    old_value: str | None
    new_value: str | None
    changed_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> ChangeLogEntry:
        """Construct from a :class:`sqlite3.Row`."""
        return cls(**dict(row))
