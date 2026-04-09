"""RequestQuestion dataclass."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class RequestQuestion:
    """An analytical question that motivated a project."""

    id: str
    project_id: str
    question_text: str
    data_period_from: str | None
    data_period_to: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> RequestQuestion:
        """Construct from a :class:`sqlite3.Row`."""
        return cls(**dict(row))
