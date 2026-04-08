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
SCHEMA_VERSION = 2

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
    2: [
        # ---------------------------------------------------------------
        # Person (SCD Type 2)
        # ---------------------------------------------------------------
        """
        CREATE TABLE IF NOT EXISTS person (
            id              TEXT PRIMARY KEY,
            first_name      TEXT NOT NULL,
            last_name       TEXT NOT NULL,
            email           TEXT,
            function_title  TEXT,
            department      TEXT,
            valid_from      TEXT NOT NULL,
            valid_to        TEXT,
            is_current      INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL
        )
        """,
        # M:N project <-> person with role
        """
        CREATE TABLE IF NOT EXISTS project_person (
            project_id  TEXT NOT NULL REFERENCES project(id),
            person_id   TEXT NOT NULL REFERENCES person(id),
            role        TEXT NOT NULL,
            PRIMARY KEY (project_id, person_id, role)
        )
        """,
        # ---------------------------------------------------------------
        # Tag
        # ---------------------------------------------------------------
        """
        CREATE TABLE IF NOT EXISTS tag (
            id       TEXT PRIMARY KEY,
            name     TEXT NOT NULL UNIQUE,
            category TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS project_tag (
            project_id TEXT NOT NULL REFERENCES project(id),
            tag_id     TEXT NOT NULL REFERENCES tag(id),
            PRIMARY KEY (project_id, tag_id)
        )
        """,
        # ---------------------------------------------------------------
        # DataFile
        # ---------------------------------------------------------------
        """
        CREATE TABLE IF NOT EXISTS data_file (
            id                TEXT PRIMARY KEY,
            project_id        TEXT NOT NULL REFERENCES project(id),
            file_path         TEXT NOT NULL,
            file_format       TEXT,
            sensitivity       TEXT,
            is_source         INTEGER NOT NULL DEFAULT 1,
            data_period_from  TEXT,
            data_period_to    TEXT,
            retention_date    TEXT,
            purged_at         TEXT,
            created_at        TEXT NOT NULL
        )
        """,
        # ---------------------------------------------------------------
        # Lookup tables
        # ---------------------------------------------------------------
        """
        CREATE TABLE IF NOT EXISTS entity_type (
            id   TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS aggregation_level (
            id   TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
        """,
        # ---------------------------------------------------------------
        # Junction tables for DataFile lookups
        # ---------------------------------------------------------------
        """
        CREATE TABLE IF NOT EXISTS data_file_entity_type (
            data_file_id   TEXT NOT NULL REFERENCES data_file(id),
            entity_type_id TEXT NOT NULL REFERENCES entity_type(id),
            PRIMARY KEY (data_file_id, entity_type_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS data_file_aggregation (
            data_file_id  TEXT NOT NULL REFERENCES data_file(id),
            agg_level_id  TEXT NOT NULL REFERENCES aggregation_level(id),
            PRIMARY KEY (data_file_id, agg_level_id)
        )
        """,
        # ---------------------------------------------------------------
        # Query
        # ---------------------------------------------------------------
        """
        CREATE TABLE IF NOT EXISTS query (
            id              TEXT PRIMARY KEY,
            output_file_id  TEXT REFERENCES data_file(id),
            source_file_id  TEXT REFERENCES data_file(id),
            query_path      TEXT NOT NULL,
            language        TEXT NOT NULL,
            sensitivity     TEXT,
            executed_at     TEXT
        )
        """,
        # ---------------------------------------------------------------
        # Deliverable
        # ---------------------------------------------------------------
        """
        CREATE TABLE IF NOT EXISTS deliverable (
            id           TEXT PRIMARY KEY,
            project_id   TEXT NOT NULL REFERENCES project(id),
            type         TEXT NOT NULL,
            file_path    TEXT,
            file_format  TEXT,
            version      TEXT,
            delivered_at TEXT,
            created_at   TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS deliverable_data_file (
            deliverable_id TEXT NOT NULL REFERENCES deliverable(id),
            data_file_id   TEXT NOT NULL REFERENCES data_file(id),
            PRIMARY KEY (deliverable_id, data_file_id)
        )
        """,
        # ---------------------------------------------------------------
        # RequestQuestion
        # ---------------------------------------------------------------
        """
        CREATE TABLE IF NOT EXISTS request_question (
            id                TEXT PRIMARY KEY,
            project_id        TEXT NOT NULL REFERENCES project(id),
            question_text     TEXT NOT NULL,
            data_period_from  TEXT,
            data_period_to    TEXT
        )
        """,
        # ---------------------------------------------------------------
        # ChangeLog (audit trail)
        # ---------------------------------------------------------------
        """
        CREATE TABLE IF NOT EXISTS change_log (
            id           TEXT PRIMARY KEY,
            entity_type  TEXT NOT NULL,
            entity_id    TEXT NOT NULL,
            field_name   TEXT NOT NULL,
            old_value    TEXT,
            new_value    TEXT,
            changed_at   TEXT NOT NULL
        )
        """,
        # ---------------------------------------------------------------
        # Seed data — common entity types
        # ---------------------------------------------------------------
        """
        INSERT OR IGNORE INTO entity_type (id, name) VALUES
            ('et-customers', 'customers'),
            ('et-transactions', 'transactions'),
            ('et-products', 'products'),
            ('et-employees', 'employees'),
            ('et-locations', 'locations'),
            ('et-events', 'events')
        """,
        # Seed data — common aggregation levels
        """
        INSERT OR IGNORE INTO aggregation_level (id, name) VALUES
            ('al-row', 'row'),
            ('al-daily', 'daily'),
            ('al-weekly', 'weekly'),
            ('al-monthly', 'monthly'),
            ('al-quarterly', 'quarterly'),
            ('al-yearly', 'yearly'),
            ('al-summary', 'summary')
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
