"""Structured JSON export for projects and their relationships.

This module is **stdlib-only**.  It gathers all metadata for a project
(or all projects) and serialises it to JSON.

Typical usage::

    from data_project_manager.core.export import export_project, export_all

    data = export_project("2026-04-07-churn-analysis")
    index = export_all()
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def export_project(
    slug: str,
    *,
    db_path: str | Path | None = None,
    config_path: Path | None = None,
) -> dict[str, Any] | None:
    """Export a single project with all relationships as a dict.

    Args:
        slug: Project slug.
        db_path: Explicit database path (skips config lookup).
        config_path: Explicit config path.

    Returns:
        Full project dict with tags, people, files, deliverables, and
        questions — or ``None`` if the slug is not found.
    """
    from data_project_manager.config.loader import get_db_path
    from data_project_manager.db.connection import get_connection

    effective_db_path = db_path or get_db_path(config_path)
    conn = get_connection(effective_db_path)
    try:
        return _build_project_export(conn, slug)
    finally:
        conn.close()


def export_all(
    *,
    db_path: str | Path | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Export an index of all projects with their relationships.

    Args:
        db_path: Explicit database path (skips config lookup).
        config_path: Explicit config path.

    Returns:
        Dict with ``exported_at``, ``count``, and ``projects`` (list).
    """
    from data_project_manager.config.loader import get_db_path
    from data_project_manager.db.connection import get_connection

    effective_db_path = db_path or get_db_path(config_path)
    conn = get_connection(effective_db_path)
    try:
        return _build_all_export(conn)
    finally:
        conn.close()


def export_project_json(
    slug: str,
    *,
    db_path: str | Path | None = None,
    config_path: Path | None = None,
    pretty: bool = True,
) -> str | None:
    """Export a single project as a JSON string.

    Args:
        slug: Project slug.
        db_path: Explicit database path.
        config_path: Explicit config path.
        pretty: Indent the JSON output.

    Returns:
        JSON string, or ``None`` if the slug is not found.
    """
    data = export_project(slug, db_path=db_path, config_path=config_path)
    if data is None:
        return None
    indent = 2 if pretty else None
    return json.dumps(data, indent=indent, ensure_ascii=False, default=str)


def export_all_json(
    *,
    db_path: str | Path | None = None,
    config_path: Path | None = None,
    pretty: bool = True,
) -> str:
    """Export the full project index as a JSON string.

    Args:
        db_path: Explicit database path.
        config_path: Explicit config path.
        pretty: Indent the JSON output.

    Returns:
        JSON string.
    """
    data = export_all(db_path=db_path, config_path=config_path)
    indent = 2 if pretty else None
    return json.dumps(data, indent=indent, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_project_export(
    conn: sqlite3.Connection,
    slug: str,
) -> dict[str, Any] | None:
    """Gather full metadata for one project."""
    from data_project_manager.db.repositories.data_file import DataFileRepository
    from data_project_manager.db.repositories.deliverable import DeliverableRepository
    from data_project_manager.db.repositories.person import ProjectPersonRepository
    from data_project_manager.db.repositories.project import ProjectRepository
    from data_project_manager.db.repositories.question import RequestQuestionRepository
    from data_project_manager.db.repositories.tag import ProjectTagRepository

    project = ProjectRepository(conn).get_by_slug(slug)
    if project is None:
        return None

    pid = project.id
    tags = ProjectTagRepository(conn).list_for_project(pid)
    people = ProjectPersonRepository(conn).list_for_project(pid)
    files = DataFileRepository(conn).list_for_project(pid)
    deliverables = DeliverableRepository(conn).list_for_project(pid)
    questions = RequestQuestionRepository(conn).list_for_project(pid)

    return {
        **asdict(project),
        "tags": [asdict(t) for t in tags],
        "people": [asdict(p) for p in people],
        "data_files": [asdict(f) for f in files],
        "deliverables": [asdict(d) for d in deliverables],
        "questions": [asdict(q) for q in questions],
        "exported_at": datetime.now(UTC).isoformat(),
    }


def _build_all_export(conn: sqlite3.Connection) -> dict[str, Any]:
    """Gather metadata for all projects."""
    from data_project_manager.db.repositories.project import ProjectRepository

    projects = ProjectRepository(conn).list()
    items = []
    for p in projects:
        slug_export = _build_project_export(conn, p.slug)
        if slug_export is not None:
            items.append(slug_export)

    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "count": len(items),
        "projects": items,
    }
