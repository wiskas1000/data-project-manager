"""Repository for RequestQuestion entities.

Example::

    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.question import RequestQuestionRepository

    conn = get_connection()
    repo = RequestQuestionRepository(conn)
    q = repo.create(
        project_id="...",
        question_text="What is the churn rate for Q1 2026?",
        data_period_from="2026-01-01",
        data_period_to="2026-03-31",
    )
"""

import sqlite3
import uuid

from data_project_manager.db.models.question import RequestQuestion


class RequestQuestionRepository:
    """CRUD operations for the ``request_question`` table.

    Request questions capture the analytical questions that motivated a
    project.  They may include optional date ranges to constrain the data
    period of interest.

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
        question_text: str,
        data_period_from: str | None = None,
        data_period_to: str | None = None,
    ) -> RequestQuestion:
        """Insert a new request question and return it.

        Args:
            project_id: UUID of the owning project.
            question_text: The analytical question being asked.
            data_period_from: ISO date for the start of the data period.
            data_period_to: ISO date for the end of the data period.

        Returns:
            The newly created :class:`RequestQuestion`.
        """
        question_id = str(uuid.uuid4())
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO request_question
                    (id, project_id, question_text,
                     data_period_from, data_period_to)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    question_id,
                    project_id,
                    question_text,
                    data_period_from,
                    data_period_to,
                ),
            )
        result = self.get(question_id)
        assert result is not None
        return result

    def get(self, question_id: str) -> RequestQuestion | None:
        """Fetch a request question by UUID.

        Args:
            question_id: UUID primary key.

        Returns:
            :class:`RequestQuestion`, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM request_question WHERE id = ?", (question_id,)
        ).fetchone()
        return RequestQuestion.from_row(row) if row is not None else None

    def list_for_project(self, project_id: str) -> list[RequestQuestion]:
        """Return all request questions for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of :class:`RequestQuestion` instances ordered by
            insertion order.
        """
        rows = self._conn.execute(
            "SELECT * FROM request_question WHERE project_id = ? ORDER BY rowid",
            (project_id,),
        ).fetchall()
        return [RequestQuestion.from_row(r) for r in rows]
