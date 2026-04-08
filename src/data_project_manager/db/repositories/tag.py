"""Repository for Tag and ProjectTag entities.

Example::

    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.tag import TagRepository

    conn = get_connection()
    repo = TagRepository(conn)
    tag = repo.create(name="logistic-regression", category="method")
"""

import sqlite3
import uuid
from typing import Any

from data_project_manager.db.repositories._helpers import row_to_dict


class TagRepository:
    """CRUD operations for the ``tag`` table.

    Tag names are normalised to lowercase on creation to prevent
    duplicates like ``"ML"`` vs ``"ml"``.

    Args:
        conn: Open SQLite connection returned by
            :func:`~data_project_manager.db.connection.get_connection`.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        *,
        name: str,
        category: str | None = None,
    ) -> dict[str, Any]:
        """Insert a new tag and return it as a dict.

        The *name* is normalised to lowercase.  If a tag with the same
        name already exists, the existing tag is returned instead.

        Args:
            name: Tag label (normalised to lowercase).
            category: Optional grouping (e.g. ``"method"``, ``"domain"``).

        Returns:
            The tag as a dict (newly created or existing).
        """
        normalised = name.strip().lower()
        existing = self.get_by_name(normalised)
        if existing is not None:
            return existing

        tag_id = str(uuid.uuid4())
        with self._conn:
            self._conn.execute(
                "INSERT INTO tag (id, name, category) VALUES (?, ?, ?)",
                (tag_id, normalised, category),
            )
        return self.get(tag_id)  # type: ignore[return-value]

    def get(self, tag_id: str) -> dict[str, Any] | None:
        """Fetch a tag by UUID.

        Args:
            tag_id: UUID primary key.

        Returns:
            Tag dict, or ``None`` if not found.
        """
        row = self._conn.execute("SELECT * FROM tag WHERE id = ?", (tag_id,)).fetchone()
        return row_to_dict(row)

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Fetch a tag by its normalised name.

        Args:
            name: Tag label (case-insensitive — compared as lowercase).

        Returns:
            Tag dict, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM tag WHERE name = ?", (name.strip().lower(),)
        ).fetchone()
        return row_to_dict(row)

    def list(self, *, category: str | None = None) -> list[dict[str, Any]]:
        """Return all tags, optionally filtered by category.

        Args:
            category: If provided, only return tags in this category.

        Returns:
            List of tag dicts ordered by name.
        """
        if category is not None:
            rows = self._conn.execute(
                "SELECT * FROM tag WHERE category = ? ORDER BY name",
                (category,),
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM tag ORDER BY name").fetchall()
        return [dict(r) for r in rows]


class ProjectTagRepository:
    """Manage the M:N relationship between projects and tags.

    Args:
        conn: Open SQLite connection.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, *, project_id: str, tag_id: str) -> None:
        """Link a tag to a project.

        Args:
            project_id: UUID of the project.
            tag_id: UUID of the tag.
        """
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO project_tag (project_id, tag_id)
                VALUES (?, ?)
                """,
                (project_id, tag_id),
            )

    def remove(self, *, project_id: str, tag_id: str) -> None:
        """Remove a tag from a project.

        Args:
            project_id: UUID of the project.
            tag_id: UUID of the tag.
        """
        with self._conn:
            self._conn.execute(
                "DELETE FROM project_tag WHERE project_id = ? AND tag_id = ?",
                (project_id, tag_id),
            )

    def list_for_project(self, project_id: str) -> list[dict[str, Any]]:
        """Return all tags for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of tag dicts ordered by name.
        """
        rows = self._conn.execute(
            """
            SELECT t.*
            FROM project_tag pt
            JOIN tag t ON t.id = pt.tag_id
            WHERE pt.project_id = ?
            ORDER BY t.name
            """,
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_projects_for_tag(self, tag_id: str) -> list[str]:
        """Return project IDs that have a given tag.

        Args:
            tag_id: UUID of the tag.

        Returns:
            List of project UUIDs.
        """
        rows = self._conn.execute(
            "SELECT project_id FROM project_tag WHERE tag_id = ?",
            (tag_id,),
        ).fetchall()
        return [r["project_id"] for r in rows]
