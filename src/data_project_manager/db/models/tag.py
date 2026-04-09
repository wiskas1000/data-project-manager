"""Tag dataclass."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Tag:
    """A label that can be attached to projects."""

    id: str
    name: str
    category: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Tag:
        """Construct from a :class:`sqlite3.Row`."""
        return cls(**dict(row))
