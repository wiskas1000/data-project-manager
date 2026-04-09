"""Repository for Query entities.

Example::

    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.query import QueryRepository

    conn = get_connection()
    repo = QueryRepository(conn)
    q = repo.create(query_path="queries/customer_ltv.sql", language="sql")
    repo.mark_executed(q["id"])
"""

import sqlite3
import uuid

from data_project_manager.db.models.query import Query
from data_project_manager.db.repositories._helpers import now_iso


class QueryRepository:
    """CRUD operations for the ``query`` table.

    Args:
        conn: Open SQLite connection returned by
            :func:`~data_project_manager.db.connection.get_connection`.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(
        self,
        *,
        query_path: str,
        language: str,
        output_file_id: str | None = None,
        source_file_id: str | None = None,
        sensitivity: str | None = None,
        executed_at: str | None = None,
    ) -> Query:
        """Insert a new query record and return it.

        Args:
            query_path: Path to the query file (e.g. ``"queries/ltv.sql"``).
            language: Query language (e.g. ``"sql"``, ``"python"``).
            output_file_id: UUID of the data file this query produces.
            source_file_id: UUID of the primary data file this query reads.
            sensitivity: Data sensitivity label inherited from the output.
            executed_at: ISO datetime of the most recent execution.

        Returns:
            The newly created :class:`Query`.
        """
        query_id = str(uuid.uuid4())
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO query
                    (id, output_file_id, source_file_id, query_path,
                     language, sensitivity, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_id,
                    output_file_id,
                    source_file_id,
                    query_path,
                    language,
                    sensitivity,
                    executed_at,
                ),
            )
        result = self.get(query_id)
        assert result is not None
        return result

    def get(self, query_id: str) -> Query | None:
        """Fetch a query by UUID.

        Args:
            query_id: UUID primary key.

        Returns:
            :class:`Query`, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM query WHERE id = ?", (query_id,)
        ).fetchone()
        return Query.from_row(row) if row is not None else None

    def list(self) -> list[Query]:
        """Return all query records ordered by query path.

        Returns:
            List of :class:`Query` instances.
        """
        rows = self._conn.execute("SELECT * FROM query ORDER BY query_path").fetchall()
        return [Query.from_row(r) for r in rows]

    def mark_executed(self, query_id: str) -> Query:
        """Set ``executed_at`` to now.

        Args:
            query_id: UUID of the query to mark.

        Returns:
            The updated :class:`Query`.

        Raises:
            ValueError: If the query does not exist.
        """
        with self._conn:
            cursor = self._conn.execute(
                "UPDATE query SET executed_at = ? WHERE id = ?",
                (now_iso(), query_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Query {query_id!r} not found.")
        result = self.get(query_id)
        assert result is not None
        return result
