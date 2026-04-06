"""SQLite connection manager for Data Project Manager.

Usage::

    from data_project_manager.db.connection import get_connection

    conn = get_connection()          # reads ~/.datapm/config.json
    conn = get_connection("/tmp/t.db")  # explicit path (tests / scripts)
"""

import sqlite3
from pathlib import Path


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open (and initialise) the SQLite database, returning a connection.

    The database is created automatically if it does not exist.  WAL mode
    is enabled so readers don't block writers.  ``row_factory`` is set to
    :class:`sqlite3.Row` so callers can access columns by name.

    Args:
        db_path: Explicit path to the ``.db`` file.  When omitted the path
            is read from ``~/.datapm/config.json`` via
            :func:`~data_project_manager.config.loader.get_db_path`.

    Returns:
        An open :class:`sqlite3.Connection` with WAL mode and row-factory
        configured.
    """
    if db_path is None:
        from data_project_manager.config.loader import get_db_path

        db_path = get_db_path()

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    from data_project_manager.db.schema import migrate

    migrate(conn)

    return conn
