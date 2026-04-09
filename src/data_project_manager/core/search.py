"""Full-text and structured project search.

This module is **stdlib-only**.  It queries the ``project_fts`` FTS5
virtual table for text search and joins against ``project``, ``tag``,
and ``project_tag`` tables for structured filters.

Typical usage::

    from data_project_manager.core.search import search_projects

    results = search_projects("churn")
    results = search_projects(
        "customer",
        domain="healthcare",
        status="active",
        tags=["logistic-regression"],
    )
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from data_project_manager.db.models.search import SearchResult


def search_projects(
    query: str | None = None,
    *,
    domain: str | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db_path: str | Path | None = None,
    config_path: Path | None = None,
) -> list[SearchResult]:
    """Search projects by text and/or structured filters.

    At least one of *query*, *domain*, *status*, *tags*, *date_from*, or
    *date_to* must be provided.

    Args:
        query: Free-text search (matched against title, description,
            slug, and domain via FTS5).
        domain: Filter by exact domain value.
        status: Filter by exact status value.
        tags: Filter to projects that have **all** of these tags.
        date_from: ISO date — only projects created on or after this date.
        date_to: ISO date — only projects created on or before this date.
        db_path: Explicit database path (skips config lookup).
        config_path: Explicit config path.

    Returns:
        List of :class:`SearchResult` ordered by relevance (when using
        text search) or creation date descending.
    """
    from data_project_manager.config.loader import get_db_path
    from data_project_manager.db.connection import get_connection

    effective_db_path = db_path or get_db_path(config_path)
    conn = get_connection(effective_db_path)
    try:
        return _execute_search(
            conn,
            query=query,
            domain=domain,
            status=status,
            tags=tags,
            date_from=date_from,
            date_to=date_to,
        )
    finally:
        conn.close()


def _execute_search(
    conn: sqlite3.Connection,
    *,
    query: str | None = None,
    domain: str | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[SearchResult]:
    """Build and run the search query against an open connection.

    This is the internal implementation used by :func:`search_projects`
    and directly by tests that manage their own connections.

    Args:
        conn: Open SQLite connection with FTS5 migration applied.
        query: Free-text search term.
        domain: Exact domain filter.
        status: Exact status filter.
        tags: Tag name filter (all must match).
        date_from: ISO date lower bound on ``created_at``.
        date_to: ISO date upper bound on ``created_at``.

    Returns:
        List of :class:`SearchResult`.
    """
    has_text = query is not None and query.strip()
    params: list[Any] = []

    if has_text:
        # FTS5 join for text relevance
        select = (
            "SELECT p.id, p.slug, p.title, p.description, p.status, "
            "p.domain, rank, p.created_at "
            "FROM project_fts fts "
            "JOIN project p ON p.id = fts.project_id "
            "WHERE project_fts MATCH ?"
        )
        # FTS5 query: quote the term for prefix matching
        fts_query = _build_fts_query(query.strip())  # type: ignore[union-attr]
        params.append(fts_query)
    else:
        select = (
            "SELECT p.id, p.slug, p.title, p.description, p.status, "
            "p.domain, 0.0 AS rank, p.created_at "
            "FROM project p "
            "WHERE 1=1"
        )

    if domain is not None:
        select += " AND p.domain = ?"
        params.append(domain)

    if status is not None:
        select += " AND p.status = ?"
        params.append(status)

    if date_from is not None:
        select += " AND p.created_at >= ?"
        params.append(date_from)

    if date_to is not None:
        select += " AND p.created_at <= ?"
        params.append(date_to + "T23:59:59")

    if tags:
        for tag_name in tags:
            select += (
                " AND p.id IN ("
                "  SELECT pt.project_id FROM project_tag pt"
                "  JOIN tag t ON t.id = pt.tag_id"
                "  WHERE t.name = ?"
                ")"
            )
            params.append(tag_name.strip().lower())

    if has_text:
        select += " ORDER BY rank"
    else:
        select += " ORDER BY p.created_at DESC"

    rows = conn.execute(select, params).fetchall()
    return [SearchResult.from_row(r) for r in rows]


def _build_fts_query(raw: str) -> str:
    """Convert a raw user query into an FTS5 query expression.

    Single words get prefix matching (``word*``).  Multi-word inputs
    are treated as an implicit AND of prefix-matched terms.

    Args:
        raw: The user's search string.

    Returns:
        FTS5 query string.
    """
    tokens = raw.split()
    if len(tokens) == 1:
        return f'"{tokens[0]}" *'
    # Multiple tokens: each as a prefix term
    return " ".join(f'"{t}" *' for t in tokens)
