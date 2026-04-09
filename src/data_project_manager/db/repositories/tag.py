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

from data_project_manager.db.models.tag import Tag


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
    ) -> Tag:
        """Insert a new tag and return it.

        The *name* is normalised to lowercase.  If a tag with the same
        name already exists, the existing tag is returned instead.

        Args:
            name: Tag label (normalised to lowercase).
            category: Optional grouping (e.g. ``"method"``, ``"domain"``).

        Returns:
            The :class:`Tag` (newly created or existing).
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
        result = self.get(tag_id)
        assert result is not None
        return result

    def get(self, tag_id: str) -> Tag | None:
        """Fetch a tag by UUID.

        Args:
            tag_id: UUID primary key.

        Returns:
            :class:`Tag`, or ``None`` if not found.
        """
        row = self._conn.execute("SELECT * FROM tag WHERE id = ?", (tag_id,)).fetchone()
        return Tag.from_row(row) if row is not None else None

    def get_by_name(self, name: str) -> Tag | None:
        """Fetch a tag by its normalised name.

        Args:
            name: Tag label (case-insensitive — compared as lowercase).

        Returns:
            :class:`Tag`, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM tag WHERE name = ?", (name.strip().lower(),)
        ).fetchone()
        return Tag.from_row(row) if row is not None else None

    def list(self, *, category: str | None = None) -> list[Tag]:
        """Return all tags, optionally filtered by category.

        Args:
            category: If provided, only return tags in this category.

        Returns:
            List of :class:`Tag` instances ordered by name.
        """
        if category is not None:
            rows = self._conn.execute(
                "SELECT * FROM tag WHERE category = ? ORDER BY name",
                (category,),
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM tag ORDER BY name").fetchall()
        return [Tag.from_row(r) for r in rows]


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

    def list_for_project(self, project_id: str) -> list[Tag]:
        """Return all tags for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of :class:`Tag` instances ordered by name.
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
        return [Tag.from_row(r) for r in rows]

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
