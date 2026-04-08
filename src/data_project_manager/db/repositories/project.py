"""Repository for Project and ProjectRoot entities.

Example::

    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.project import ProjectRepository

    conn = get_connection()
    repo = ProjectRepository(conn)
    project = repo.create(title="Churn analysis", domain="marketing")
    projects = repo.list()
"""

from __future__ import annotations

import sqlite3
import uuid
from typing import TYPE_CHECKING, Any

from data_project_manager.db.repositories._helpers import now_iso, row_to_dict

if TYPE_CHECKING:
    from data_project_manager.db.repositories.changelog import ChangeLogRepository


class ProjectRootRepository:
    """CRUD operations for the ``project_root`` table.

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
        absolute_path: str,
        is_default: bool = False,
    ) -> dict[str, Any]:
        """Insert a new project root and return it as a dict.

        Args:
            name: Human-readable label (e.g. ``"work"``).
            absolute_path: Full filesystem path to the root directory.
            is_default: Whether this root is the active default.

        Returns:
            The newly created root as a dict.
        """
        root_id = str(uuid.uuid4())
        created_at = now_iso()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO project_root
                    (id, name, absolute_path, is_default, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (root_id, name, absolute_path, int(is_default), created_at),
            )
        return self.get(root_id)  # type: ignore[return-value]

    def get(self, root_id: str) -> dict[str, Any] | None:
        """Fetch a root by its UUID.

        Args:
            root_id: UUID primary key.

        Returns:
            Root dict, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM project_root WHERE id = ?", (root_id,)
        ).fetchone()
        return row_to_dict(row)

    def get_by_name(self, name: str) -> dict[str, Any] | None:
        """Fetch a root by its label.

        Args:
            name: Root label (e.g. ``"work"``).

        Returns:
            Root dict, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM project_root WHERE name = ?", (name,)
        ).fetchone()
        return row_to_dict(row)

    def get_default(self) -> dict[str, Any] | None:
        """Return the default root, or ``None`` if none is marked default.

        Returns:
            Root dict, or ``None``.
        """
        row = self._conn.execute(
            "SELECT * FROM project_root WHERE is_default = 1 LIMIT 1"
        ).fetchone()
        return row_to_dict(row)

    def list(self) -> list[dict[str, Any]]:
        """Return all roots ordered by name.

        Returns:
            List of root dicts.
        """
        rows = self._conn.execute("SELECT * FROM project_root ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def set_default(self, root_id: str) -> None:
        """Mark *root_id* as the default, clearing any previous default.

        Args:
            root_id: UUID of the root to make default.
        """
        with self._conn:
            self._conn.execute("UPDATE project_root SET is_default = 0")
            self._conn.execute(
                "UPDATE project_root SET is_default = 1 WHERE id = ?", (root_id,)
            )


class ProjectRepository:
    """CRUD operations for the ``project`` table.

    Args:
        conn: Open SQLite connection returned by
            :func:`~data_project_manager.db.connection.get_connection`.
    """

    VALID_STATUSES = {"active", "paused", "done", "archived"}

    #: Columns that may be changed via :meth:`update`.
    UPDATABLE_COLUMNS = {
        "title",
        "description",
        "status",
        "is_adhoc",
        "domain",
        "root_id",
        "external_url",
        "request_date",
        "expected_start",
        "expected_end",
        "realized_start",
        "realized_end",
        "estimated_hours",
        "relative_path",
        "has_git_repo",
        "template_used",
    }

    def __init__(
        self,
        conn: sqlite3.Connection,
        changelog: ChangeLogRepository | None = None,
    ) -> None:
        self._conn = conn
        self._changelog = changelog

    def create(
        self,
        *,
        title: str,
        slug: str,
        description: str | None = None,
        status: str = "active",
        is_adhoc: bool = False,
        domain: str | None = None,
        root_id: str | None = None,
        external_url: str | None = None,
        request_date: str | None = None,
        expected_start: str | None = None,
        expected_end: str | None = None,
        realized_start: str | None = None,
        realized_end: str | None = None,
        estimated_hours: float | None = None,
        relative_path: str | None = None,
        has_git_repo: bool = False,
        template_used: str | None = None,
    ) -> dict[str, Any]:
        """Insert a new project and return it as a dict.

        Args:
            title: Human-readable project name.
            slug: URL-safe identifier (``YYYY-MM-DD-short-name``).
            description: Free-text description.
            status: One of ``active``, ``paused``, ``done``, ``archived``.
            is_adhoc: ``True`` for quick ad-hoc requests.
            domain: Subject area (e.g. ``"healthcare"``).
            root_id: FK to ``project_root.id``.
            external_url: Link to Trello/DevOps board.
            request_date: ISO date when the request was received.
            expected_start: ISO date for planned start.
            expected_end: ISO date for planned end.
            realized_start: ISO date for actual start.
            realized_end: ISO date for actual end.
            estimated_hours: Effort estimate in hours.
            relative_path: Folder path relative to the root.
            has_git_repo: Whether ``git init`` was run.
            template_used: Name of the scaffold template.

        Returns:
            The newly created project as a dict.

        Raises:
            ValueError: If *status* is not one of the valid values.
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status {status!r}. Must be one of {self.VALID_STATUSES}."
            )
        project_id = str(uuid.uuid4())
        now = now_iso()
        try:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO project (
                        id, slug, title, description, status, is_adhoc, domain,
                        root_id, external_url, request_date, expected_start,
                        expected_end, realized_start, realized_end,
                        estimated_hours, relative_path, has_git_repo,
                        template_used, created_at, updated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?
                    )
                    """,
                    (
                        project_id,
                        slug,
                        title,
                        description,
                        status,
                        int(is_adhoc),
                        domain,
                        root_id,
                        external_url,
                        request_date,
                        expected_start,
                        expected_end,
                        realized_start,
                        realized_end,
                        estimated_hours,
                        relative_path,
                        int(has_git_repo),
                        template_used,
                        now,
                        now,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            if "slug" in str(exc).lower() or "unique" in str(exc).lower():
                raise ValueError(
                    f"A project with slug {slug!r} already exists. "
                    f"Choose a different title or wait until tomorrow."
                ) from exc
            raise
        return self.get(project_id)  # type: ignore[return-value]

    def get(self, project_id: str) -> dict[str, Any] | None:
        """Fetch a project by its UUID.

        Args:
            project_id: UUID primary key.

        Returns:
            Project dict, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM project WHERE id = ?", (project_id,)
        ).fetchone()
        return row_to_dict(row)

    def get_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Fetch a project by its slug.

        Args:
            slug: Unique slug (e.g. ``"2026-04-06-churn-analysis"``).

        Returns:
            Project dict, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM project WHERE slug = ?", (slug,)
        ).fetchone()
        return row_to_dict(row)

    def list(
        self,
        *,
        status: str | None = None,
        domain: str | None = None,
        root_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return projects, optionally filtered.

        Args:
            status: Filter by status.
            domain: Filter by domain.
            root_id: Filter by root.

        Returns:
            List of project dicts ordered by ``created_at`` descending.
        """
        query = "SELECT * FROM project WHERE 1=1"
        params: list[Any] = []
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        if domain is not None:
            query += " AND domain = ?"
            params.append(domain)
        if root_id is not None:
            query += " AND root_id = ?"
            params.append(root_id)
        query += " ORDER BY created_at DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def update(
        self,
        project_id: str,
        **fields: Any,
    ) -> dict[str, Any] | None:
        """Update one or more fields on a project.

        Only the keys present in *fields* are changed.  ``updated_at`` is
        always refreshed automatically.

        Args:
            project_id: UUID of the project to update.
            **fields: Column-value pairs to update.  Valid keys match the
                column names in the ``project`` table.

        Returns:
            The updated project dict, or ``None`` if not found.

        Raises:
            ValueError: If an invalid *status* value is supplied.
        """
        if not fields:
            return self.get(project_id)

        bad_keys = set(fields) - self.UPDATABLE_COLUMNS
        if bad_keys:
            raise ValueError(
                f"Cannot update immutable or unknown column(s): {bad_keys}. "
                f"Allowed: {sorted(self.UPDATABLE_COLUMNS)}"
            )

        if "status" in fields and fields["status"] not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status {fields['status']!r}. "
                f"Must be one of {self.VALID_STATUSES}."
            )

        # Snapshot before-values for changelog (only when changelog is wired up)
        before = self.get(project_id) if self._changelog is not None else None

        user_fields = dict(fields)  # preserve before adding updated_at
        fields["updated_at"] = now_iso()
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [project_id]
        with self._conn:
            self._conn.execute(
                f"UPDATE project SET {set_clause} WHERE id = ?",  # noqa: S608
                values,
            )
            if before is not None and self._changelog is not None:
                for key, new_val in user_fields.items():
                    old_val = before.get(key)
                    if str(old_val) != str(new_val):
                        self._conn.execute(
                            """
                            INSERT INTO change_log
                                (id, entity_type, entity_id, field_name,
                                 old_value, new_value, changed_at)
                            VALUES (?, 'project', ?, ?, ?, ?, ?)
                            """,
                            (
                                str(uuid.uuid4()),
                                project_id,
                                key,
                                None if old_val is None else str(old_val),
                                None if new_val is None else str(new_val),
                                now_iso(),
                            ),
                        )
        return self.get(project_id)
