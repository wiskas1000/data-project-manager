"""Shared test helpers (non-fixture utilities)."""

import sqlite3

from data_project_manager.db.repositories.project import ProjectRepository
from data_project_manager.db.schema import migrate


def fresh_conn() -> sqlite3.Connection:
    """Return a migrated in-memory SQLite connection."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn)
    return conn


def make_project(conn: sqlite3.Connection, title: str = "Test") -> dict:
    """Create a minimal project and return it."""
    return ProjectRepository(conn).create(
        title=title,
        slug=f"2026-01-01-{title.lower().replace(' ', '-')}",
    )
