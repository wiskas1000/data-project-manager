"""Repository for DataFile, EntityType, AggregationLevel, and their junction tables.

Example::

    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.data_file import DataFileRepository

    conn = get_connection()
    repo = DataFileRepository(conn)
    f = repo.create(
        project_id="...",
        file_path="data/raw/customers_2026Q1.csv",
        sensitivity="client_confidential",
    )
"""

import sqlite3
import uuid

from data_project_manager.db.models.data_file import (
    AggregationLevel,
    DataFile,
    EntityType,
)
from data_project_manager.db.repositories._helpers import now_iso


class EntityTypeRepository:
    """Read/write access to the ``entity_type`` lookup table.

    The table is pre-populated with seed data during migration.  This
    repository lets callers list existing types and add custom ones.

    Args:
        conn: Open SQLite connection.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, *, name: str) -> EntityType:
        """Insert a new entity type and return it.

        The *name* is normalised to lowercase.  If a type with the same
        name already exists the existing record is returned unchanged.

        Args:
            name: Entity type label (normalised to lowercase).

        Returns:
            The :class:`EntityType` (newly created or existing).
        """
        normalised = name.strip().lower()
        existing = self.get_by_name(normalised)
        if existing is not None:
            return existing
        type_id = str(uuid.uuid4())
        with self._conn:
            self._conn.execute(
                "INSERT INTO entity_type (id, name) VALUES (?, ?)",
                (type_id, normalised),
            )
        result = self.get(type_id)
        assert result is not None
        return result

    def get(self, type_id: str) -> EntityType | None:
        """Fetch an entity type by UUID.

        Args:
            type_id: UUID primary key.

        Returns:
            :class:`EntityType`, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM entity_type WHERE id = ?", (type_id,)
        ).fetchone()
        return EntityType.from_row(row) if row is not None else None

    def get_by_name(self, name: str) -> EntityType | None:
        """Fetch an entity type by name (case-insensitive).

        Args:
            name: Name to look up (compared as lowercase).

        Returns:
            :class:`EntityType`, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM entity_type WHERE name = ?",
            (name.strip().lower(),),
        ).fetchone()
        return EntityType.from_row(row) if row is not None else None

    def list(self) -> list[EntityType]:
        """Return all entity types ordered by name.

        Returns:
            List of :class:`EntityType` instances.
        """
        rows = self._conn.execute("SELECT * FROM entity_type ORDER BY name").fetchall()
        return [EntityType.from_row(r) for r in rows]


class AggregationLevelRepository:
    """Read/write access to the ``aggregation_level`` lookup table.

    The table is pre-populated with seed data during migration.

    Args:
        conn: Open SQLite connection.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create(self, *, name: str) -> AggregationLevel:
        """Insert a new aggregation level and return it.

        The *name* is normalised to lowercase.  If a level with the same
        name already exists the existing record is returned unchanged.

        Args:
            name: Aggregation level label (normalised to lowercase).

        Returns:
            The :class:`AggregationLevel` (newly created or existing).
        """
        normalised = name.strip().lower()
        existing = self.get_by_name(normalised)
        if existing is not None:
            return existing
        level_id = str(uuid.uuid4())
        with self._conn:
            self._conn.execute(
                "INSERT INTO aggregation_level (id, name) VALUES (?, ?)",
                (level_id, normalised),
            )
        result = self.get(level_id)
        assert result is not None
        return result

    def get(self, level_id: str) -> AggregationLevel | None:
        """Fetch an aggregation level by UUID.

        Args:
            level_id: UUID primary key.

        Returns:
            :class:`AggregationLevel`, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM aggregation_level WHERE id = ?", (level_id,)
        ).fetchone()
        return AggregationLevel.from_row(row) if row is not None else None

    def get_by_name(self, name: str) -> AggregationLevel | None:
        """Fetch an aggregation level by name (case-insensitive).

        Args:
            name: Name to look up (compared as lowercase).

        Returns:
            :class:`AggregationLevel`, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM aggregation_level WHERE name = ?",
            (name.strip().lower(),),
        ).fetchone()
        return AggregationLevel.from_row(row) if row is not None else None

    def list(self) -> list[AggregationLevel]:
        """Return all aggregation levels ordered by name.

        Returns:
            List of :class:`AggregationLevel` instances.
        """
        rows = self._conn.execute(
            "SELECT * FROM aggregation_level ORDER BY name"
        ).fetchall()
        return [AggregationLevel.from_row(r) for r in rows]


class DataFileRepository:
    """CRUD operations for the ``data_file`` table.

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
        file_path: str,
        file_format: str | None = None,
        sensitivity: str | None = None,
        is_source: bool = True,
        data_period_from: str | None = None,
        data_period_to: str | None = None,
        retention_date: str | None = None,
    ) -> DataFile:
        """Insert a new data file record and return it.

        Args:
            project_id: UUID of the owning project.
            file_path: Path to the file, relative to the project root.
            file_format: File extension or format (e.g. ``"csv"``, ``"parquet"``).
            sensitivity: Data sensitivity label (e.g. ``"client_confidential"``).
            is_source: ``True`` if this is source/input data; ``False`` for
                derived/output data.
            data_period_from: ISO date for the start of the data period.
            data_period_to: ISO date for the end of the data period.
            retention_date: ISO date after which the file may be purged.

        Returns:
            The newly created :class:`DataFile`.
        """
        file_id = str(uuid.uuid4())
        now = now_iso()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO data_file
                    (id, project_id, file_path, file_format, sensitivity,
                     is_source, data_period_from, data_period_to,
                     retention_date, purged_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    file_id,
                    project_id,
                    file_path,
                    file_format,
                    sensitivity,
                    1 if is_source else 0,
                    data_period_from,
                    data_period_to,
                    retention_date,
                    now,
                ),
            )
        result = self.get(file_id)
        assert result is not None
        return result

    def get(self, file_id: str) -> DataFile | None:
        """Fetch a data file by UUID.

        Args:
            file_id: UUID primary key.

        Returns:
            :class:`DataFile`, or ``None`` if not found.
        """
        row = self._conn.execute(
            "SELECT * FROM data_file WHERE id = ?", (file_id,)
        ).fetchone()
        return DataFile.from_row(row) if row is not None else None

    def list_for_project(self, project_id: str) -> list[DataFile]:
        """Return all data files for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of :class:`DataFile` instances ordered by file path.
        """
        rows = self._conn.execute(
            "SELECT * FROM data_file WHERE project_id = ? ORDER BY file_path",
            (project_id,),
        ).fetchall()
        return [DataFile.from_row(r) for r in rows]

    def mark_purged(self, file_id: str) -> DataFile:
        """Set ``purged_at`` to now for a data file.

        Args:
            file_id: UUID of the file to mark as purged.

        Returns:
            The updated :class:`DataFile`.

        Raises:
            ValueError: If the file does not exist.
        """
        with self._conn:
            cursor = self._conn.execute(
                "UPDATE data_file SET purged_at = ? WHERE id = ?",
                (now_iso(), file_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"DataFile {file_id!r} not found.")
        result = self.get(file_id)
        assert result is not None
        return result


class DataFileEntityTypeRepository:
    """Manage the M:N relationship between data files and entity types.

    Args:
        conn: Open SQLite connection.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, *, data_file_id: str, entity_type_id: str) -> None:
        """Link an entity type to a data file.

        Args:
            data_file_id: UUID of the data file.
            entity_type_id: UUID of the entity type.
        """
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO data_file_entity_type
                    (data_file_id, entity_type_id)
                VALUES (?, ?)
                """,
                (data_file_id, entity_type_id),
            )

    def remove(self, *, data_file_id: str, entity_type_id: str) -> None:
        """Remove an entity type link from a data file.

        Args:
            data_file_id: UUID of the data file.
            entity_type_id: UUID of the entity type.
        """
        with self._conn:
            self._conn.execute(
                """
                DELETE FROM data_file_entity_type
                WHERE data_file_id = ? AND entity_type_id = ?
                """,
                (data_file_id, entity_type_id),
            )

    def list_for_file(self, data_file_id: str) -> list[EntityType]:
        """Return all entity types for a data file.

        Args:
            data_file_id: UUID of the data file.

        Returns:
            List of :class:`EntityType` instances ordered by name.
        """
        rows = self._conn.execute(
            """
            SELECT et.*
            FROM data_file_entity_type dfet
            JOIN entity_type et ON et.id = dfet.entity_type_id
            WHERE dfet.data_file_id = ?
            ORDER BY et.name
            """,
            (data_file_id,),
        ).fetchall()
        return [EntityType.from_row(r) for r in rows]


class DataFileAggregationRepository:
    """Manage the M:N relationship between data files and aggregation levels.

    Args:
        conn: Open SQLite connection.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, *, data_file_id: str, agg_level_id: str) -> None:
        """Link an aggregation level to a data file.

        Args:
            data_file_id: UUID of the data file.
            agg_level_id: UUID of the aggregation level.
        """
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO data_file_aggregation
                    (data_file_id, agg_level_id)
                VALUES (?, ?)
                """,
                (data_file_id, agg_level_id),
            )

    def remove(self, *, data_file_id: str, agg_level_id: str) -> None:
        """Remove an aggregation level link from a data file.

        Args:
            data_file_id: UUID of the data file.
            agg_level_id: UUID of the aggregation level.
        """
        with self._conn:
            self._conn.execute(
                """
                DELETE FROM data_file_aggregation
                WHERE data_file_id = ? AND agg_level_id = ?
                """,
                (data_file_id, agg_level_id),
            )

    def list_for_file(self, data_file_id: str) -> list[AggregationLevel]:
        """Return all aggregation levels for a data file.

        Args:
            data_file_id: UUID of the data file.

        Returns:
            List of :class:`AggregationLevel` instances ordered by name.
        """
        rows = self._conn.execute(
            """
            SELECT al.*
            FROM data_file_aggregation dfa
            JOIN aggregation_level al ON al.id = dfa.agg_level_id
            WHERE dfa.data_file_id = ?
            ORDER BY al.name
            """,
            (data_file_id,),
        ).fetchall()
        return [AggregationLevel.from_row(r) for r in rows]
