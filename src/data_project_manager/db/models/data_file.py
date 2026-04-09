"""DataFile, EntityType, and AggregationLevel dataclasses."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class EntityType:
    """A lookup value describing what entities a data file contains."""

    id: str
    name: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> EntityType:
        """Construct from a :class:`sqlite3.Row`."""
        return cls(**dict(row))


@dataclass(frozen=True)
class AggregationLevel:
    """A lookup value describing the granularity of a data file."""

    id: str
    name: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> AggregationLevel:
        """Construct from a :class:`sqlite3.Row`."""
        return cls(**dict(row))


@dataclass(frozen=True)
class DataFile:
    """A data file registered against a project."""

    id: str
    project_id: str
    file_path: str
    file_format: str | None
    sensitivity: str | None
    is_source: bool
    data_period_from: str | None
    data_period_to: str | None
    retention_date: str | None
    purged_at: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> DataFile:
        """Construct from a :class:`sqlite3.Row`."""
        d = dict(row)
        d["is_source"] = bool(d["is_source"])
        return cls(**d)
