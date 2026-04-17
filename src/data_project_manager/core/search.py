"""Full-text and structured project search.

This module is **stdlib-only**.  It queries the ``project_fts`` FTS5
virtual table for text search and joins against ``project``, ``tag``,
and ``project_tag`` tables for structured filters.

Two entry points are exposed:

* :func:`search_projects` — FTS5 relevance search with exact-match
  filters.  Great when the user knows a word that appears in the title,
  description, slug, or domain.
* :func:`search_project_metadata` — substring (``LIKE``) search over
  metadata associated with projects (tags, people, entity types,
  aggregation levels, request questions, deliverable paths).  Used to
  surface projects whose FTS5 columns don't match but whose metadata
  does.

Callers that want a single merged result set (FTS5 first, metadata
matches appended) should call both and de-duplicate by passing the
FTS5 result IDs via ``exclude_ids`` to :func:`search_project_metadata`.
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
    entity_types: list[str] | None = None,
    aggregation_levels: list[str] | None = None,
    requestor: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    db_path: str | Path | None = None,
    config_path: Path | None = None,
) -> list[SearchResult]:
    """Search projects by FTS5 text and/or structured filters.

    At least one of *query* or a filter kwarg must be provided.

    Args:
        query: Free-text search (matched against title, description,
            slug, and domain via FTS5).
        domain: Filter by exact domain value.
        status: Filter by exact status value.
        tags: Filter to projects that have **all** of these tags.
        entity_types: Filter to projects with at least one data file
            tagged with **all** of these entity type names.
        aggregation_levels: Filter to projects with at least one data
            file tagged with **all** of these aggregation level names.
        requestor: Case-insensitive substring match against the name or
            email of a person linked to the project with
            ``role='requestor'`` (current SCD2 row).
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
            entity_types=entity_types,
            aggregation_levels=aggregation_levels,
            requestor=requestor,
            date_from=date_from,
            date_to=date_to,
        )
    finally:
        conn.close()


def search_project_metadata(
    query: str | None = None,
    *,
    domain: str | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
    entity_types: list[str] | None = None,
    aggregation_levels: list[str] | None = None,
    requestor: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    exclude_ids: list[str] | None = None,
    db_path: str | Path | None = None,
    config_path: Path | None = None,
) -> list[SearchResult]:
    """Substring search across project metadata (Tier 1 sources).

    *query* is matched case-insensitively (via ``LOWER(...) LIKE ?``)
    against:

    * ``tag.name``
    * ``person.first_name || ' ' || person.last_name`` and
      ``person.email`` (any role, current SCD2 row only)
    * ``entity_type.name``
    * ``aggregation_level.name``
    * ``request_question.question_text``
    * ``deliverable.file_path``

    The structured kwargs are identical in meaning to
    :func:`search_projects` and are applied on top of the substring
    match (so filter buttons can restrict both result sets uniformly).

    Args:
        query: Substring to match against the metadata sources above.
            May be ``None`` — in that case only the filter kwargs apply.
        domain: Filter by exact domain value.
        status: Filter by exact status value.
        tags: Require **all** of these tag names.
        entity_types: Require **all** of these entity type names.
        aggregation_levels: Require **all** of these aggregation level names.
        requestor: Case-insensitive substring match against the requestor
            person's name or email.
        date_from: ISO date — only projects created on or after this date.
        date_to: ISO date — only projects created on or before this date.
        exclude_ids: Project IDs to exclude (for de-duping against a
            prior FTS5 result set).
        db_path: Explicit database path.
        config_path: Explicit config path.

    Returns:
        List of :class:`SearchResult` with ``rank = 0.0``, ordered by
        ``created_at`` descending.
    """
    from data_project_manager.config.loader import get_db_path
    from data_project_manager.db.connection import get_connection

    effective_db_path = db_path or get_db_path(config_path)
    conn = get_connection(effective_db_path)
    try:
        return _execute_metadata_search(
            conn,
            query=query,
            domain=domain,
            status=status,
            tags=tags,
            entity_types=entity_types,
            aggregation_levels=aggregation_levels,
            requestor=requestor,
            date_from=date_from,
            date_to=date_to,
            exclude_ids=exclude_ids,
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
    entity_types: list[str] | None = None,
    aggregation_levels: list[str] | None = None,
    requestor: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[SearchResult]:
    """Build and run an FTS5 search against an open connection.

    Internal entry point used by :func:`search_projects` and tests that
    manage their own connections.
    """
    has_text = query is not None and query.strip()
    params: list[Any] = []

    if has_text:
        sql = (
            "SELECT p.id, p.slug, p.title, p.description, p.status, "
            "p.domain, rank, p.created_at "
            "FROM project_fts fts "
            "JOIN project p ON p.id = fts.project_id "
            "WHERE project_fts MATCH ?"
        )
        params.append(_build_fts_query(query.strip()))  # type: ignore[union-attr]
    else:
        sql = (
            "SELECT p.id, p.slug, p.title, p.description, p.status, "
            "p.domain, 0.0 AS rank, p.created_at "
            "FROM project p "
            "WHERE 1=1"
        )

    sql, params = _apply_filters(
        sql,
        params,
        domain=domain,
        status=status,
        tags=tags,
        entity_types=entity_types,
        aggregation_levels=aggregation_levels,
        requestor=requestor,
        date_from=date_from,
        date_to=date_to,
    )

    sql += " ORDER BY rank" if has_text else " ORDER BY p.created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    return [SearchResult.from_row(r) for r in rows]


def _execute_metadata_search(
    conn: sqlite3.Connection,
    *,
    query: str | None = None,
    domain: str | None = None,
    status: str | None = None,
    tags: list[str] | None = None,
    entity_types: list[str] | None = None,
    aggregation_levels: list[str] | None = None,
    requestor: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    exclude_ids: list[str] | None = None,
) -> list[SearchResult]:
    """Build and run a metadata substring search against an open connection."""
    params: list[Any] = []
    sql = (
        "SELECT DISTINCT p.id, p.slug, p.title, p.description, p.status, "
        "p.domain, 0.0 AS rank, p.created_at "
        "FROM project p "
        "WHERE 1=1"
    )

    if query is not None and query.strip():
        like = "%" + _escape_like(query.strip().lower()) + "%"
        sql += (
            " AND ("
            # tag name
            " EXISTS (SELECT 1 FROM project_tag pt JOIN tag t ON t.id = pt.tag_id"
            "         WHERE pt.project_id = p.id"
            "         AND LOWER(t.name) LIKE ? ESCAPE '\\')"
            # person name or email (any role, current SCD2 row)
            " OR EXISTS (SELECT 1 FROM project_person pp JOIN person pe"
            "            ON pe.id = pp.person_id"
            "            WHERE pp.project_id = p.id AND pe.is_current = 1"
            "            AND (LOWER(pe.first_name || ' ' || pe.last_name)"
            "                 LIKE ? ESCAPE '\\'"
            "                 OR LOWER(COALESCE(pe.email, '')) LIKE ? ESCAPE '\\'))"
            # entity type
            " OR EXISTS (SELECT 1 FROM data_file df"
            "            JOIN data_file_entity_type dfe ON dfe.data_file_id = df.id"
            "            JOIN entity_type et ON et.id = dfe.entity_type_id"
            "            WHERE df.project_id = p.id"
            "            AND LOWER(et.name) LIKE ? ESCAPE '\\')"
            # aggregation level
            " OR EXISTS (SELECT 1 FROM data_file df"
            "            JOIN data_file_aggregation dfa ON dfa.data_file_id = df.id"
            "            JOIN aggregation_level al ON al.id = dfa.agg_level_id"
            "            WHERE df.project_id = p.id"
            "            AND LOWER(al.name) LIKE ? ESCAPE '\\')"
            # request question text
            " OR EXISTS (SELECT 1 FROM request_question rq"
            "            WHERE rq.project_id = p.id"
            "            AND LOWER(rq.question_text) LIKE ? ESCAPE '\\')"
            # deliverable file path
            " OR EXISTS (SELECT 1 FROM deliverable d"
            "            WHERE d.project_id = p.id"
            "            AND LOWER(COALESCE(d.file_path, '')) LIKE ? ESCAPE '\\')"
            ")"
        )
        # 7 placeholders: tag, person name, email, entity, agg, question, deliverable
        params.extend([like] * 7)

    sql, params = _apply_filters(
        sql,
        params,
        domain=domain,
        status=status,
        tags=tags,
        entity_types=entity_types,
        aggregation_levels=aggregation_levels,
        requestor=requestor,
        date_from=date_from,
        date_to=date_to,
    )

    if exclude_ids:
        placeholders = ",".join("?" * len(exclude_ids))
        sql += f" AND p.id NOT IN ({placeholders})"
        params.extend(exclude_ids)

    sql += " ORDER BY p.created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    return [SearchResult.from_row(r) for r in rows]


def _apply_filters(
    sql: str,
    params: list[Any],
    *,
    domain: str | None,
    status: str | None,
    tags: list[str] | None,
    entity_types: list[str] | None,
    aggregation_levels: list[str] | None,
    requestor: str | None,
    date_from: str | None,
    date_to: str | None,
) -> tuple[str, list[Any]]:
    """Append shared structured filter clauses to an in-progress query."""
    if domain is not None:
        sql += " AND p.domain = ?"
        params.append(domain)

    if status is not None:
        sql += " AND p.status = ?"
        params.append(status)

    if date_from is not None:
        sql += " AND p.created_at >= ?"
        params.append(date_from)

    if date_to is not None:
        sql += " AND p.created_at <= ?"
        params.append(date_to + "T23:59:59")

    if tags:
        for tag_name in tags:
            sql += (
                " AND p.id IN ("
                "  SELECT pt.project_id FROM project_tag pt"
                "  JOIN tag t ON t.id = pt.tag_id"
                "  WHERE t.name = ?"
                ")"
            )
            params.append(tag_name.strip().lower())

    if entity_types:
        for name in entity_types:
            sql += (
                " AND p.id IN ("
                "  SELECT df.project_id FROM data_file df"
                "  JOIN data_file_entity_type dfe ON dfe.data_file_id = df.id"
                "  JOIN entity_type et ON et.id = dfe.entity_type_id"
                "  WHERE et.name = ?"
                ")"
            )
            params.append(name.strip().lower())

    if aggregation_levels:
        for name in aggregation_levels:
            sql += (
                " AND p.id IN ("
                "  SELECT df.project_id FROM data_file df"
                "  JOIN data_file_aggregation dfa ON dfa.data_file_id = df.id"
                "  JOIN aggregation_level al ON al.id = dfa.agg_level_id"
                "  WHERE al.name = ?"
                ")"
            )
            params.append(name.strip().lower())

    if requestor is not None and requestor.strip():
        like = "%" + _escape_like(requestor.strip().lower()) + "%"
        sql += (
            " AND p.id IN ("
            "  SELECT pp.project_id FROM project_person pp"
            "  JOIN person pe ON pe.id = pp.person_id"
            "  WHERE pp.role = 'requestor' AND pe.is_current = 1"
            "  AND (LOWER(pe.first_name || ' ' || pe.last_name) LIKE ? ESCAPE '\\'"
            "       OR LOWER(COALESCE(pe.email, '')) LIKE ? ESCAPE '\\')"
            ")"
        )
        params.extend([like, like])

    return sql, params


def _escape_like(raw: str) -> str:
    """Escape LIKE wildcards so user input can't act as a pattern."""
    return raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _build_fts_query(raw: str) -> str:
    """Convert a raw user query into an FTS5 query expression.

    Single words get prefix matching (``word*``).  Multi-word inputs
    are treated as an implicit AND of prefix-matched terms.
    """
    tokens = raw.split()
    if len(tokens) == 1:
        return f'"{tokens[0]}" *'
    return " ".join(f'"{t}" *' for t in tokens)
