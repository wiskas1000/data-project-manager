"""Query dataclass."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Query:
    """A SQL or Python query that transforms data within a project."""

    id: str
    output_file_id: str | None
    source_file_id: str | None
    query_path: str
    language: str
    sensitivity: str | None
    executed_at: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Query:
        """Construct from a :class:`sqlite3.Row`."""
        return cls(**dict(row))
