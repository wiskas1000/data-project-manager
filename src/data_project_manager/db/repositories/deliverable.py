"""Repository for Deliverable and DeliverableDataFile entities.

Example::

    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.deliverable import DeliverableRepository

    conn = get_connection()
    repo = DeliverableRepository(conn)
    d = repo.create(project_id="...", type="report", file_path="output/report_Q1.pdf")
"""

import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any


def _now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert a :class:`sqlite3.Row` to a plain dict, or return ``None``."""
    return dict(row) if row is not None else None


class DeliverableRepository:
    """CRUD operations for the ``deliverable`` table.

    Args:
        conn: Open SQLite connection returned by
            :func:`~data_project_manager.db.connection.get_connection`.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        *,
        project_id: str,
        type: str,
        file_path: str | None = None,
        file_format: str | None = None,
        version: str | None = None,
        delivered_at: str | None = None,
    ) -> dict[str, Any]:
        """Insert a new deliverable and return it as a dict.

        Args:
            project_id: UUID of the owning project.
            type: Deliverable type (e.g. ``"report"``, ``"dashboard"``).
            file_path: Optional path to the deliverable file.
            file_format: File extension or format (e.g. ``"pdf"``, ``"xlsx"``).
            version: Optional version label (e.g. ``"v1.0"``).
            delivered_at: ISO datetime when the deliverable was sent.

        Returns:
            The newly created deliverable as a dict.
        """
        deliverable_id = str(uuid.uuid4())
        now = _now()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO deliverable
                    (id, project_id, type, file_path, file_format,
                     version, delivered_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    deliverable_id,
                    project_id,
                    type,
                    file_path,
                    file_format,
                    version,
                    delivered_at,
                    now,
                ),
            )
        return self.get(deliverable_id)  # type: ignore[return-value]

    def get(self, deliverable_id: str) -> dict[str, Any] | None:
        """Fetch a deliverable by UUID.

        Args:
            deliverable_id: UUID primary key.

        Returns:
            Deliverable dict, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM deliverable WHERE id = ?", (deliverable_id,)
        ).fetchone()
        return _row_to_dict(row)

    def list_for_project(self, project_id: str) -> list[dict[str, Any]]:
        """Return all deliverables for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of deliverable dicts ordered by created_at descending.
        """
        rows = self._conn.execute(
            "SELECT * FROM deliverable WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_delivered(self, deliverable_id: str) -> dict[str, Any]:
        """Set ``delivered_at`` to now.

        Args:
            deliverable_id: UUID of the deliverable to mark.

        Returns:
            The updated deliverable dict.

        Raises:
            ValueError: If the deliverable does not exist.
        """
        if self.get(deliverable_id) is None:
            raise ValueError(f"Deliverable {deliverable_id!r} not found.")
        with self._conn:
            self._conn.execute(
                "UPDATE deliverable SET delivered_at = ? WHERE id = ?",
                (_now(), deliverable_id),
            )
        return self.get(deliverable_id)  # type: ignore[return-value]


class DeliverableDataFileRepository:
    """Manage the M:N relationship between deliverables and data files.

    Args:
        conn: Open SQLite connection.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, *, deliverable_id: str, data_file_id: str) -> None:
        """Link a data file to a deliverable.

        Args:
            deliverable_id: UUID of the deliverable.
            data_file_id: UUID of the data file.
        """
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO deliverable_data_file
                    (deliverable_id, data_file_id)
                VALUES (?, ?)
                """,
                (deliverable_id, data_file_id),
            )

    def remove(self, *, deliverable_id: str, data_file_id: str) -> None:
        """Remove a data file link from a deliverable.

        Args:
            deliverable_id: UUID of the deliverable.
            data_file_id: UUID of the data file.
        """
        with self._conn:
            self._conn.execute(
                """
                DELETE FROM deliverable_data_file
                WHERE deliverable_id = ? AND data_file_id = ?
                """,
                (deliverable_id, data_file_id),
            )

    def list_for_deliverable(self, deliverable_id: str) -> list[dict[str, Any]]:
        """Return all data files linked to a deliverable.

        Args:
            deliverable_id: UUID of the deliverable.

        Returns:
            List of data file dicts ordered by file path.
        """
        rows = self._conn.execute(
            """
            SELECT df.*
            FROM deliverable_data_file ddf
            JOIN data_file df ON df.id = ddf.data_file_id
            WHERE ddf.deliverable_id = ?
            ORDER BY df.file_path
            """,
            (deliverable_id,),
        ).fetchall()
        return [dict(r) for r in rows]
