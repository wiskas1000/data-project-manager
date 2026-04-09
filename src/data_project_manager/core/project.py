"""Business logic for project creation and folder scaffolding.

This module is **stdlib-only**.  No optional dependencies may be imported
here.

Typical usage::

    from data_project_manager.core.project import create_project

    result = create_project(
        title="Churn analysis",
        domain="marketing",
        archetype="analysis",
        do_git_init=True,
    )
    print(result["slug"])        # 2026-04-07-churn-analysis
    print(result["project_path"])
"""

import json
import re
import subprocess
import unicodedata
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from data_project_manager.core.templates import (
    BASE_FOLDERS,
    SRC_TOGGLES,
    SUBFOLDERS,
    folder_display_name,
    resolve_folders,
    subfolder_display_name,
)

# ---------------------------------------------------------------------------
# Slug & folder-name helpers
# ---------------------------------------------------------------------------


def slugify(text: str) -> str:
    """Convert arbitrary text to a lowercase, hyphen-separated ASCII slug.

    Unicode characters are transliterated to their ASCII equivalents where
    possible (e.g. ``é`` → ``e``).  All remaining non-alphanumeric characters
    are replaced with hyphens; consecutive hyphens are collapsed.

    Args:
        text: Input string (may contain Unicode, spaces, punctuation).

    Returns:
        URL-safe lowercase slug, e.g. ``"churn-analysis"``.

    Examples:
        >>> slugify("Churn Analysis!")
        'churn-analysis'
        >>> slugify("Hépatite C — étude 2026")
        'hepatite-c-etude-2026'
    """
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def generate_slug(title: str, today: date | None = None) -> str:
    """Build a dated slug from a project title.

    Args:
        title: Human-readable project title.
        today: Date prefix; defaults to :func:`datetime.date.today`.

    Returns:
        Slug in the form ``YYYY-MM-DD-short-name``.

    Examples:
        >>> from datetime import date
        >>> generate_slug("Churn Analysis", date(2026, 4, 7))
        '2026-04-07-churn-analysis'
    """
    d = today or date.today()
    return f"{d.isoformat()}-{slugify(title)}"


def make_folder_name(title: str, today: date | None = None) -> str:
    """Build the project folder name.

    Spaces in the title are replaced with hyphens; original casing is
    preserved.  The result is prefixed with the ISO date and an underscore.

    Args:
        title: Human-readable project title.
        today: Date prefix; defaults to :func:`datetime.date.today`.

    Returns:
        Folder name, e.g. ``"2026-04-07_Churn-Analysis"``.

    Examples:
        >>> from datetime import date
        >>> make_folder_name("Churn Analysis", date(2026, 4, 7))
        '2026-04-07_Churn-Analysis'
    """
    d = today or date.today()
    folder_title = re.sub(r"\s+", "-", title.strip())
    return f"{d.isoformat()}_{folder_title}"


# ---------------------------------------------------------------------------
# Scaffolding
# ---------------------------------------------------------------------------


def scaffold_folders(
    project_path: Path,
    optional_folders: list[str] | None = None,
    *,
    language: str = "nl",
) -> None:
    """Create the folder structure inside *project_path*.

    Always creates the base folders (``communicatie/``, ``documenten/``).
    Additional subtrees are created for each key in *optional_folders*.
    ``notebooks`` and ``queries`` are placed under ``src/``.

    Args:
        project_path: Root of the new project (created if absent).
        optional_folders: Resolved folder keys (output of
            :func:`~data_project_manager.core.templates.resolve_folders`).
        language: ``"nl"`` or ``"en"`` — controls on-disk folder names.
    """
    project_path.mkdir(parents=True, exist_ok=True)

    # Base folders (always)
    for key in BASE_FOLDERS:
        (project_path / folder_display_name(key, language)).mkdir(exist_ok=True)

    for key in optional_folders or []:
        # src/ children (notebooks, queries) go under src/
        if key in SRC_TOGGLES:
            src_name = folder_display_name("src", language)
            child_name = subfolder_display_name(key, language)
            (project_path / src_name / child_name).mkdir(parents=True, exist_ok=True)
            continue

        # Top-level optional folder
        folder_name = folder_display_name(key, language)
        (project_path / folder_name).mkdir(exist_ok=True)

        # Auto-created children (data/raw, data/processed, etc.)
        for child_key in SUBFOLDERS.get(key, []):
            child_name = subfolder_display_name(child_key, language)
            (project_path / folder_name / child_name).mkdir(exist_ok=True)


def export_project_json(project: dict[str, Any] | Any, project_path: Path) -> Path:
    """Write *project* metadata to ``project.json`` inside *project_path*.

    Args:
        project: Project dataclass or dict (as returned by
            :class:`~data_project_manager.db.repositories.project.ProjectRepository`).
        project_path: Root of the project folder.

    Returns:
        Path to the written ``project.json`` file.
    """
    from dataclasses import asdict

    raw = asdict(project) if hasattr(project, "__dataclass_fields__") else dict(project)
    export: dict[str, Any] = {k: v for k, v in raw.items() if k != "project_path"}
    export["exported_at"] = datetime.now(UTC).isoformat()

    json_path = project_path / "project.json"
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(export, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return json_path


def git_init_project(src_path: Path) -> bool:
    """Run ``git init`` inside the ``src/`` directory.

    Git lives in ``src/`` rather than the project root so that
    OneDrive-synced project folders don't conflict with ``.git/``
    internals.  See ``docs/FOLDER-SELECTION-DESIGN.md`` Section 6.

    Args:
        src_path: The ``src/`` directory to initialise.

    Returns:
        ``True`` if ``git init`` succeeded, ``False`` if git is
        unavailable, *src_path* does not exist, or the command failed.
    """
    if not src_path.is_dir():
        return False

    try:
        result = subprocess.run(
            ["git", "init"],
            cwd=src_path,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False  # git not on PATH

    if result.returncode != 0:
        return False

    gitignore = src_path / ".gitignore"
    gitignore.write_text(
        "# datapm default — add language-specific patterns as needed\n"
        "__pycache__/\n"
        "*.pyc\n"
        ".ipynb_checkpoints/\n",
        encoding="utf-8",
    )
    return True


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


def create_project(
    title: str,
    *,
    domain: str | None = None,
    description: str | None = None,
    is_adhoc: bool = False,
    optional_folders: list[str] | None = None,
    do_git_init: bool = False,
    root_name: str | None = None,
    root_path_override: Path | None = None,
    request_date: str | None = None,
    expected_start: str | None = None,
    expected_end: str | None = None,
    estimated_hours: float | None = None,
    template_used: str = "analysis",
    language: str = "nl",
    db_path: str | Path | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Create a new project end-to-end.

    Performs, in order:

    1. Slug and folder-name generation.
    2. ProjectRoot resolution (config → DB; created in DB if absent).
    3. DB record insertion via
       :class:`~data_project_manager.db.repositories.project.ProjectRepository`.
    4. Folder scaffolding (base + optional, language-aware).
    5. Optional ``git init`` in ``src/``.
    6. ``project.json`` export.

    Args:
        title: Human-readable project title.
        domain: Subject area (e.g. ``"healthcare"``).
        description: Free-text description.
        is_adhoc: ``True`` for quick ad-hoc requests.
        optional_folders: Resolved folder keys.  When ``None``, the
            archetype indicated by *template_used* provides defaults.
        do_git_init: Run ``git init`` in the ``src/`` directory.
        root_name: Named root from config; defaults to the config default.
        root_path_override: Explicit root path (skips config lookup).
            Useful in tests.
        request_date: ISO date the request was received.
        expected_start: ISO date for planned start.
        expected_end: ISO date for planned end.
        estimated_hours: Effort estimate in hours.
        template_used: Archetype key (e.g. ``"analysis"``).
        language: ``"nl"`` or ``"en"`` for on-disk folder names.
        db_path: Explicit database path (skips config lookup).  Useful in
            tests.
        config_path: Explicit config path (skips default).  Useful in tests.

    Returns:
        Project dict with an extra ``"project_path"`` key containing the
        absolute path to the created folder as a string.

    Raises:
        FileExistsError: If the project folder already exists.
    """
    from data_project_manager.config.loader import (
        get_db_path,
        get_default_root,
        get_root_path,
        load_config,
    )
    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.project import (
        ProjectRepository,
        ProjectRootRepository,
    )

    # If no explicit folders, use archetype defaults
    if optional_folders is None:
        from data_project_manager.core.templates import get_archetype

        archetype = get_archetype(template_used)
        optional_folders = resolve_folders(archetype.folders)
    else:
        optional_folders = resolve_folders(optional_folders)

    today = date.today()
    slug = generate_slug(title, today)
    folder_name = make_folder_name(title, today)

    # -- Resolve root --------------------------------------------------------
    effective_db_path = db_path or get_db_path(config_path)
    conn = get_connection(effective_db_path)
    try:
        root_repo = ProjectRootRepository(conn)
        proj_repo = ProjectRepository(conn)

        root_id: str | None = None
        project_root_path: Path | None = root_path_override

        if project_root_path is None:
            resolved_root_name = root_name or get_default_root(config_path)
            if resolved_root_name:
                root_record = root_repo.get_by_name(resolved_root_name)
                if root_record is None:
                    cfg_root_path = get_root_path(resolved_root_name, config_path)
                    if cfg_root_path:
                        config = load_config(config_path)
                        is_def = resolved_root_name == config.get("general", {}).get(
                            "default_root"
                        )
                        root_record = root_repo.create(
                            name=resolved_root_name,
                            absolute_path=str(cfg_root_path),
                            is_default=is_def,
                        )
                if root_record:
                    root_id = root_record.id
                    project_root_path = Path(root_record.absolute_path)

        project_path = (
            (project_root_path / folder_name)
            if project_root_path
            else (Path.cwd() / folder_name)
        )

        if project_path.exists():
            raise FileExistsError(f"Project folder already exists: {project_path}")

        # -- DB record -------------------------------------------------------
        project = proj_repo.create(
            title=title,
            slug=slug,
            description=description,
            is_adhoc=is_adhoc,
            domain=domain,
            root_id=root_id,
            relative_path=folder_name,
            has_git_repo=do_git_init,
            template_used=template_used,
            request_date=request_date,
            expected_start=expected_start,
            expected_end=expected_end,
            estimated_hours=estimated_hours,
        )

        # -- Scaffold --------------------------------------------------------
        scaffold_folders(project_path, optional_folders, language=language)

        if do_git_init:
            src_name = folder_display_name("src", language)
            src_dir = project_path / src_name
            did_init = git_init_project(src_dir)
            if not did_init:
                proj_repo.update(project.id, has_git_repo=False)
                project = proj_repo.get(project.id)  # type: ignore[assignment]

        export_project_json(project, project_path)

        from dataclasses import asdict

        return {**asdict(project), "project_path": str(project_path)}
    finally:
        conn.close()


def list_projects(
    *,
    status: str | None = None,
    domain: str | None = None,
    db_path: str | Path | None = None,
    config_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Return projects from the database, optionally filtered.

    Args:
        status: Filter by status.
        domain: Filter by domain.
        db_path: Explicit database path.
        config_path: Explicit config path.

    Returns:
        List of project dicts ordered by ``created_at`` descending.
    """
    from data_project_manager.config.loader import get_db_path
    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.project import ProjectRepository

    effective_db_path = db_path or get_db_path(config_path)
    conn = get_connection(effective_db_path)
    try:
        return ProjectRepository(conn).list(status=status, domain=domain)
    finally:
        conn.close()
