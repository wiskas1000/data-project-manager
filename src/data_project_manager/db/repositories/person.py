"""Repository for Person (SCD2) and ProjectPerson entities.

Example::

    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.person import PersonRepository

    conn = get_connection()
    repo = PersonRepository(conn)
    person = repo.create(first_name="Jane", last_name="Doe", department="Analytics")
    new_version = repo.create_new_version(person["id"], department="Data Science")
"""

import sqlite3
import uuid
from datetime import UTC, date, datetime
from typing import Any


def _now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def _today() -> str:
    """Return today's date as an ISO 8601 string."""
    return date.today().isoformat()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert a :class:`sqlite3.Row` to a plain dict, or return ``None``."""
    return dict(row) if row is not None else None


class PersonRepository:
    """CRUD operations for the ``person`` table with SCD Type 2 versioning.

    When a person's attributes change (department, title, etc.), call
    :meth:`create_new_version` instead of updating in place.  This closes
    the current version (sets ``valid_to`` and ``is_current = 0``) and
    inserts a new row with the updated values.

    Args:
        conn: Open SQLite connection returned by
            :func:`~data_project_manager.db.connection.get_connection`.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str | None = None,
        function_title: str | None = None,
        department: str | None = None,
        valid_from: str | None = None,
    ) -> dict[str, Any]:
        """Insert a new person and return it as a dict.

        Args:
            first_name: Given name.
            last_name: Family name.
            email: Email address.
            function_title: Job title.
            department: Department.
            valid_from: ISO date when this version becomes active.
                Defaults to today.

        Returns:
            The newly created person as a dict.
        """
        person_id = str(uuid.uuid4())
        now = _now()
        vf = valid_from or _today()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO person
                    (id, first_name, last_name, email, function_title,
                     department, valid_from, valid_to, is_current, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 1, ?)
                """,
                (
                    person_id,
                    first_name,
                    last_name,
                    email,
                    function_title,
                    department,
                    vf,
                    now,
                ),
            )
        return self.get(person_id)  # type: ignore[return-value]

    def get(self, person_id: str) -> dict[str, Any] | None:
        """Fetch a person by UUID.

        Args:
            person_id: UUID primary key.

        Returns:
            Person dict, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM person WHERE id = ?", (person_id,)
        ).fetchone()
        return _row_to_dict(row)

    def get_current_by_email(self, email: str) -> dict[str, Any] | None:
        """Fetch the current version of a person by email.

        Args:
            email: Email address.

        Returns:
            Person dict, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM person WHERE email = ? AND is_current = 1",
            (email,),
        ).fetchone()
        return _row_to_dict(row)

    def list(self, *, current_only: bool = True) -> list[dict[str, Any]]:
        """Return persons, optionally only current versions.

        Args:
            current_only: If ``True`` (default), return only rows where
                ``is_current = 1``.

        Returns:
            List of person dicts ordered by last name, first name.
        """
        if current_only:
            query = "SELECT * FROM person WHERE is_current = 1"
        else:
            query = "SELECT * FROM person"
        query += " ORDER BY last_name, first_name"
        rows = self._conn.execute(query).fetchall()
        return [dict(r) for r in rows]

    def create_new_version(
        self,
        person_id: str,
        *,
        valid_from: str | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        """Create a new SCD2 version of an existing person.

        Closes the current version by setting ``valid_to`` and
        ``is_current = 0``, then inserts a new row carrying forward
        all fields not explicitly overridden.

        Args:
            person_id: UUID of the current version to supersede.
            valid_from: ISO date for the new version.  Defaults to today.
            **fields: Fields to change (e.g. ``department="Data Science"``).

        Returns:
            The newly created version as a dict.

        Raises:
            ValueError: If the person does not exist or is not current.
        """
        current = self.get(person_id)
        if current is None:
            raise ValueError(f"Person {person_id!r} not found.")
        if not current["is_current"]:
            raise ValueError(f"Person {person_id!r} is not the current version.")

        vf = valid_from or _today()
        now = _now()
        new_id = str(uuid.uuid4())

        # Carry forward all fields, override with provided ones
        new_first = fields.get("first_name", current["first_name"])
        new_last = fields.get("last_name", current["last_name"])
        new_email = fields.get("email", current["email"])
        new_title = fields.get("function_title", current["function_title"])
        new_dept = fields.get("department", current["department"])

        with self._conn:
            # Close current version
            self._conn.execute(
                "UPDATE person SET valid_to = ?, is_current = 0 WHERE id = ?",
                (vf, person_id),
            )
            # Insert new version
            self._conn.execute(
                """
                INSERT INTO person
                    (id, first_name, last_name, email, function_title,
                     department, valid_from, valid_to, is_current, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 1, ?)
                """,
                (new_id, new_first, new_last, new_email, new_title, new_dept, vf, now),
            )
        return self.get(new_id)  # type: ignore[return-value]


class ProjectPersonRepository:
    """Manage the M:N relationship between projects and persons.

    Args:
        conn: Open SQLite connection.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, *, project_id: str, person_id: str, role: str) -> None:
        """Link a person to a project with a given role.

        Args:
            project_id: UUID of the project.
            person_id: UUID of the person.
            role: Role label (e.g. ``"requestor"``, ``"reviewer"``).
        """
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO project_person
                    (project_id, person_id, role)
                VALUES (?, ?, ?)
                """,
                (project_id, person_id, role),
            )

    def remove(self, *, project_id: str, person_id: str, role: str) -> None:
        """Remove a person-role link from a project.

        Args:
            project_id: UUID of the project.
            person_id: UUID of the person.
            role: Role label to remove.
        """
        with self._conn:
            self._conn.execute(
                """
                DELETE FROM project_person
                WHERE project_id = ? AND person_id = ? AND role = ?
                """,
                (project_id, person_id, role),
            )

    def list_for_project(self, project_id: str) -> list[dict[str, Any]]:
        """Return all person-role entries for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of dicts with ``person_id``, ``role``, and full person
            fields joined from the ``person`` table.
        """
        rows = self._conn.execute(
            """
            SELECT pp.role, p.*
            FROM project_person pp
            JOIN person p ON p.id = pp.person_id
            WHERE pp.project_id = ?
            ORDER BY pp.role, p.last_name
            """,
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_for_person(self, person_id: str) -> list[dict[str, Any]]:
        """Return all project-role entries for a person.

        Args:
            person_id: UUID of the person.

        Returns:
            List of dicts with ``project_id`` and ``role``.
        """
        rows = self._conn.execute(
            """
            SELECT project_id, role
            FROM project_person
            WHERE person_id = ?
            ORDER BY role
            """,
            (person_id,),
        ).fetchall()
        return [dict(r) for r in rows]
