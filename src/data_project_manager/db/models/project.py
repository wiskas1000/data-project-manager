"""Project dataclass."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    """A data-analysis project with scheduling and metadata."""

    id: str
    slug: str
    title: str
    description: str | None
    status: str
    is_adhoc: bool
    domain: str | None
    root_id: str | None
    external_url: str | None
    request_date: str | None
    expected_start: str | None
    expected_end: str | None
    realized_start: str | None
    realized_end: str | None
    estimated_hours: float | None
    relative_path: str | None
    has_git_repo: bool
    template_used: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Project:
        """Construct from a :class:`sqlite3.Row`."""
        d = dict(row)
        d["is_adhoc"] = bool(d["is_adhoc"])
        d["has_git_repo"] = bool(d["has_git_repo"])
        return cls(**d)
