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
from datetime import UTC, datetime
from typing import Any


def _now() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert a :class:`sqlite3.Row` to a plain dict, or return ``None``."""
    return dict(row) if row is not None else None


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
    ) -> dict[str, Any]:
        """Insert a new query record and return it as a dict.

        Args:
            query_path: Path to the query file (e.g. ``"queries/ltv.sql"``).
            language: Query language (e.g. ``"sql"``, ``"python"``).
            output_file_id: UUID of the data file this query produces.
            source_file_id: UUID of the primary data file this query reads.
            sensitivity: Data sensitivity label inherited from the output.
            executed_at: ISO datetime of the most recent execution.

        Returns:
            The newly created query as a dict.
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
        return self.get(query_id)  # type: ignore[return-value]

    def get(self, query_id: str) -> dict[str, Any] | None:
        """Fetch a query by UUID.

        Args:
            query_id: UUID primary key.

        Returns:
            Query dict, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM query WHERE id = ?", (query_id,)
        ).fetchone()
        return _row_to_dict(row)

    def list(self) -> list[dict[str, Any]]:
        """Return all query records ordered by query path.

        Returns:
            List of query dicts.
        """
        rows = self._conn.execute("SELECT * FROM query ORDER BY query_path").fetchall()
        return [dict(r) for r in rows]

    def mark_executed(self, query_id: str) -> dict[str, Any]:
        """Set ``executed_at`` to now.

        Args:
            query_id: UUID of the query to mark.

        Returns:
            The updated query dict.

        Raises:
            ValueError: If the query does not exist.
        """
        if self.get(query_id) is None:
            raise ValueError(f"Query {query_id!r} not found.")
        with self._conn:
            self._conn.execute(
                "UPDATE query SET executed_at = ? WHERE id = ?",
                (_now(), query_id),
            )
        return self.get(query_id)  # type: ignore[return-value]
