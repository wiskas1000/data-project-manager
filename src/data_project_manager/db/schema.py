"""Version-based DDL migration system for Data Project Manager.

Every schema change gets a new migration number.  On startup
:func:`migrate` advances the database from its current version to
:data:`SCHEMA_VERSION` by running each pending migration in order.

Migration history
-----------------
- **1** — Project and ProjectRoot tables (v0.1.0)
- **2** — Remaining 14 tables: Person, Tag, DataFile, Query, Deliverable,
  RequestQuestion, ChangeLog, EntityType, AggregationLevel, and all
  junction tables (v0.2.0)
"""

import sqlite3

#: The schema version this codebase expects.  Bump when adding a migration.
SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# DDL statements grouped by migration version
# ---------------------------------------------------------------------------

MIGRATIONS: dict[int, list[str]] = {
    1: [
        # Tracks the applied migration version.
        """
        CREATE TABLE IF NOT EXISTS _schema_version (
            version INTEGER NOT NULL
        )
        """,
        "INSERT INTO _schema_version (version) VALUES (0)",
        # A named filesystem root under which projects live.
        """
        CREATE TABLE IF NOT EXISTS project_root (
            id           TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            absolute_path TEXT NOT NULL UNIQUE,
            is_default   INTEGER NOT NULL DEFAULT 0,
            created_at   TEXT NOT NULL
        )
        """,
        # Central project entity.
        """
        CREATE TABLE IF NOT EXISTS project (
            id               TEXT PRIMARY KEY,
            slug             TEXT NOT NULL UNIQUE,
            title            TEXT NOT NULL,
            description      TEXT,
            status           TEXT NOT NULL DEFAULT 'active',
            is_adhoc         INTEGER NOT NULL DEFAULT 0,
            domain           TEXT,
            root_id          TEXT REFERENCES project_root(id),
            external_url     TEXT,
            request_date     TEXT,
            expected_start   TEXT,
            expected_end     TEXT,
            realized_start   TEXT,
            realized_end     TEXT,
            estimated_hours  REAL,
            relative_path    TEXT,
            has_git_repo     INTEGER NOT NULL DEFAULT 0,
            template_used    TEXT,
            created_at       TEXT NOT NULL,
            updated_at       TEXT NOT NULL
        )
        """,
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def migrate(conn: sqlite3.Connection) -> None:
    """Advance the database schema to :data:`SCHEMA_VERSION`.

    Safe to call on every startup — it is a no-op when the database is
    already up to date.

    Args:
        conn: Open SQLite connection with ``foreign_keys=ON``.
    """
    current = _get_schema_version(conn)
    for version in range(current + 1, SCHEMA_VERSION + 1):
        with conn:
            for statement in MIGRATIONS[version]:
                conn.execute(statement)
            if version > 0:
                conn.execute("UPDATE _schema_version SET version = ?", (version,))


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the schema version recorded in the database.

    Args:
        conn: Open SQLite connection.

    Returns:
        Integer version, or ``0`` if the version table does not exist yet.
    """
    return _get_schema_version(conn)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_schema_version(conn: sqlite3.Connection) -> int:
    """Read the current schema version without raising if the table is absent."""
    try:
        row = conn.execute("SELECT version FROM _schema_version").fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0
