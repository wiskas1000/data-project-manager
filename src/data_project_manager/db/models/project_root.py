"""ProjectRoot dataclass."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectRoot:
    """A root directory that contains project folders."""

    id: str
    name: str
    absolute_path: str
    is_default: bool
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> ProjectRoot:
        """Construct from a :class:`sqlite3.Row`."""
        d = dict(row)
        d["is_default"] = bool(d["is_default"])
        return cls(**d)
