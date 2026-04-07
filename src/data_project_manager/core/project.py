"""Business logic for project creation and folder scaffolding.

This module is **stdlib-only**.  No optional dependencies may be imported
here.

Typical usage::

    from data_project_manager.core.project import create_project

    result = create_project(
        title="Churn analysis",
        domain="marketing",
        optional_folders=["data", "notebooks"],
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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Subfolders created in every new project.
STANDARD_FOLDERS: list[str] = ["archief", "communicatie", "documenten"]

#: Optional folder groups and the subfolders they create.
OPTIONAL_FOLDER_MAP: dict[str, list[str]] = {
    "data": ["data/raw", "data/processed", "data/metadata"],
    "src": ["src/queries"],
    "literatuur": ["literatuur"],
    "resultaten": ["resultaten/export", "resultaten/figuren"],
    "notebooks": ["notebooks"],
}

#: Valid keys for *optional_folders* argument.
OPTIONAL_FOLDER_KEYS: list[str] = list(OPTIONAL_FOLDER_MAP)


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
) -> None:
    """Create the standard folder structure inside *project_path*.

    Always creates ``archief/``, ``communicatie/``, and ``documenten/``.
    Additional subtrees are created for each key in *optional_folders*.

    Args:
        project_path: Root of the new project (created if absent).
        optional_folders: Subset of :data:`OPTIONAL_FOLDER_KEYS` to add.
    """
    project_path.mkdir(parents=True, exist_ok=True)
    for folder in STANDARD_FOLDERS:
        (project_path / folder).mkdir(exist_ok=True)
    for key in optional_folders or []:
        for subfolder in OPTIONAL_FOLDER_MAP.get(key, []):
            (project_path / subfolder).mkdir(parents=True, exist_ok=True)


def export_project_json(project: dict[str, Any], project_path: Path) -> Path:
    """Write *project* metadata to ``project.json`` inside *project_path*.

    Args:
        project: Project dict (as returned by
            :class:`~data_project_manager.db.repositories.project.ProjectRepository`).
        project_path: Root of the project folder.

    Returns:
        Path to the written ``project.json`` file.
    """
    export: dict[str, Any] = {
        k: v
        for k, v in project.items()
        if k != "project_path"  # strip runtime-only key
    }
    export["exported_at"] = datetime.now(UTC).isoformat()

    json_path = project_path / "project.json"
    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(export, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return json_path


def git_init_project(project_path: Path) -> bool:
    """Run ``git init`` in *project_path* and write a minimal ``.gitignore``.

    Args:
        project_path: Directory to initialise.

    Returns:
        ``True`` if ``git init`` succeeded, ``False`` if git is unavailable
        or returned a non-zero exit code.
    """
    try:
        result = subprocess.run(
            ["git", "init"],
            cwd=project_path,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False  # git not on PATH

    if result.returncode != 0:
        return False

    gitignore = project_path / ".gitignore"
    gitignore.write_text(
        "# Data Project Manager\n*.db\n.DS_Store\n__pycache__/\n",
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
    template_used: str = "minimal",
    db_path: str | Path | None = None,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Create a new project end-to-end.

    Performs, in order:

    1. Slug and folder-name generation.
    2. ProjectRoot resolution (config → DB; created in DB if absent).
    3. DB record insertion via
       :class:`~data_project_manager.db.repositories.project.ProjectRepository`.
    4. Folder scaffolding.
    5. Optional ``git init``.
    6. ``project.json`` export.

    Args:
        title: Human-readable project title.
        domain: Subject area (e.g. ``"healthcare"``).
        description: Free-text description.
        is_adhoc: ``True`` for quick ad-hoc requests.
        optional_folders: Subset of :data:`OPTIONAL_FOLDER_KEYS`.
        do_git_init: Run ``git init`` in the project folder.
        root_name: Named root from config; defaults to the config default.
        root_path_override: Explicit root path (skips config lookup).
            Useful in tests.
        request_date: ISO date the request was received.
        expected_start: ISO date for planned start.
        expected_end: ISO date for planned end.
        estimated_hours: Effort estimate in hours.
        template_used: Scaffold template name.
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

    today = date.today()
    slug = generate_slug(title, today)
    folder_name = make_folder_name(title, today)

    # -- Resolve root --------------------------------------------------------
    effective_db_path = db_path or get_db_path(config_path)
    conn = get_connection(effective_db_path)
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
                root_id = root_record["id"]
                project_root_path = Path(root_record["absolute_path"])

    project_path = (
        (project_root_path / folder_name)
        if project_root_path
        else (Path.cwd() / folder_name)
    )

    if project_path.exists():
        raise FileExistsError(f"Project folder already exists: {project_path}")

    # -- DB record -----------------------------------------------------------
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

    # -- Scaffold ------------------------------------------------------------
    scaffold_folders(project_path, optional_folders)

    if do_git_init:
        did_init = git_init_project(project_path)
        if not did_init:
            # Update DB record to reflect git didn't actually run.
            proj_repo.update(project["id"], has_git_repo=False)
            project = proj_repo.get(project["id"])  # type: ignore[assignment]

    export_project_json(project, project_path)

    return {**project, "project_path": str(project_path)}


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
    return ProjectRepository(conn).list(status=status, domain=domain)
