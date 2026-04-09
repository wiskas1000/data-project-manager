"""Deliverable dataclass."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Deliverable:
    """An output artefact delivered to a stakeholder."""

    id: str
    project_id: str
    type: str
    file_path: str | None
    file_format: str | None
    version: str | None
    delivered_at: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Deliverable:
        """Construct from a :class:`sqlite3.Row`."""
        return cls(**dict(row))
