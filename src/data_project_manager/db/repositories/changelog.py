"""Repository for ChangeLog entities.

The ChangeLog records field-level changes to any entity.  It is written
to automatically when a supporting repository makes a change — callers
do not need to write to it directly.

Example::

    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.changelog import ChangeLogRepository
    from data_project_manager.db.repositories.project import ProjectRepository

    conn = get_connection()
    changelog = ChangeLogRepository(conn)
    repo = ProjectRepository(conn, changelog=changelog)

    repo.update(project_id, status="done")
    # → ChangeLog records: field_name="status", old="active", new="done"

    history = changelog.list_for_entity("project", project_id)
"""

import sqlite3
import uuid
from typing import Any

from data_project_manager.db.repositories._helpers import now_iso, row_to_dict


class ChangeLogRepository:
    """Read/write access to the ``change_log`` table.

    Entries are written via :meth:`log`.  Supporting repositories
    (e.g. :class:`~data_project_manager.db.repositories.project.ProjectRepository`)
    accept a ``changelog`` constructor argument and call :meth:`log`
    automatically when records change.

    Args:
        conn: Open SQLite connection returned by
            :func:`~data_project_manager.db.connection.get_connection`.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def log(
        self,
        *,
        entity_type: str,
        entity_id: str,
        field_name: str,
        old_value: str | None,
        new_value: str | None,
    ) -> dict[str, Any]:
        """Insert a single change-log entry and return it as a dict.

        Args:
            entity_type: Name of the table that changed (e.g. ``"project"``).
            entity_id: UUID of the changed record.
            field_name: Name of the column that changed.
            old_value: Previous value as a string, or ``None``.
            new_value: New value as a string, or ``None``.

        Returns:
            The newly created log entry as a dict.
        """
        entry_id = str(uuid.uuid4())
        changed_at = now_iso()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO change_log
                    (id, entity_type, entity_id, field_name,
                     old_value, new_value, changed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry_id,
                    entity_type,
                    entity_id,
                    field_name,
                    old_value,
                    new_value,
                    changed_at,
                ),
            )
        return self.get(entry_id)  # type: ignore[return-value]

    def get(self, entry_id: str) -> dict[str, Any] | None:
        """Fetch a log entry by UUID.

        Args:
            entry_id: UUID primary key.

        Returns:
            Log entry dict, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM change_log WHERE id = ?", (entry_id,)
        ).fetchone()
        return row_to_dict(row)

    def list_for_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """Return all log entries for a specific record.

        Args:
            entity_type: Table name (e.g. ``"project"``).
            entity_id: UUID of the record.

        Returns:
            List of log entry dicts ordered by ``changed_at`` ascending.
        """
        rows = self._conn.execute(
            """
            SELECT * FROM change_log
            WHERE entity_type = ? AND entity_id = ?
            ORDER BY changed_at
            """,
            (entity_type, entity_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_for_field(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str,
    ) -> list[dict[str, Any]]:
        """Return the change history for a single field on a record.

        Args:
            entity_type: Table name (e.g. ``"project"``).
            entity_id: UUID of the record.
            field_name: Column name to filter by.

        Returns:
            List of log entry dicts ordered by ``changed_at`` ascending.
        """
        rows = self._conn.execute(
            """
            SELECT * FROM change_log
            WHERE entity_type = ? AND entity_id = ? AND field_name = ?
            ORDER BY changed_at
            """,
            (entity_type, entity_id, field_name),
        ).fetchall()
        return [dict(r) for r in rows]
