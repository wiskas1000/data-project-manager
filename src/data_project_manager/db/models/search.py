"""Search result dataclass."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    """A project search result with relevance rank.

    Attributes:
        id: Project UUID.
        slug: URL-safe identifier.
        title: Human-readable project name.
        description: Free-text description.
        status: One of ``active``, ``paused``, ``done``, ``archived``.
        domain: Subject area.
        rank: FTS5 relevance score (lower is more relevant).
        created_at: ISO timestamp.
    """

    id: str
    slug: str
    title: str
    description: str | None
    status: str
    domain: str | None
    rank: float
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> SearchResult:
        """Build from a joined ``project`` + ``project_fts`` query row."""
        d = dict(row)
        return cls(**d)
