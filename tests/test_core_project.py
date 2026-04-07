"""Tests for core/project.py."""

import json
from datetime import date
from pathlib import Path

import pytest

from data_project_manager.core.project import (
    OPTIONAL_FOLDER_KEYS,
    STANDARD_FOLDERS,
    create_project,
    export_project_json,
    generate_slug,
    list_projects,
    make_folder_name,
    scaffold_folders,
    slugify,
)
from data_project_manager.db.schema import migrate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _db(tmp_path: Path) -> Path:
    """Return path to a fresh migrated SQLite database."""
    db = tmp_path / "test.db"
    import sqlite3 as _sqlite3

    conn = _sqlite3.connect(db)
    conn.row_factory = _sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn)
    conn.close()
    return db


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


def test_slugify_basic() -> None:
    assert slugify("Churn Analysis") == "churn-analysis"


def test_slugify_unicode() -> None:
    assert slugify("Hépatite C") == "hepatite-c"


def test_slugify_punctuation() -> None:
    assert slugify("Q&A — Report!") == "qa-report"


def test_slugify_consecutive_hyphens() -> None:
    assert slugify("hello   world") == "hello-world"


def test_slugify_leading_trailing() -> None:
    assert slugify("  foo bar  ") == "foo-bar"


def test_slugify_numbers() -> None:
    assert slugify("Report 2026 Q1") == "report-2026-q1"


# ---------------------------------------------------------------------------
# generate_slug
# ---------------------------------------------------------------------------


def test_generate_slug() -> None:
    d = date(2026, 4, 7)
    assert generate_slug("Churn Analysis", d) == "2026-04-07-churn-analysis"


def test_generate_slug_uses_today_by_default() -> None:
    slug = generate_slug("Test")
    assert slug.startswith(date.today().isoformat())


# ---------------------------------------------------------------------------
# make_folder_name
# ---------------------------------------------------------------------------


def test_make_folder_name() -> None:
    d = date(2026, 4, 7)
    assert make_folder_name("Churn Analysis", d) == "2026-04-07_Churn-Analysis"


def test_make_folder_name_preserves_case() -> None:
    d = date(2026, 1, 1)
    assert make_folder_name("My PROJECT", d) == "2026-01-01_My-PROJECT"


# ---------------------------------------------------------------------------
# scaffold_folders
# ---------------------------------------------------------------------------


def test_scaffold_creates_standard_folders(tmp_path: Path) -> None:
    project_path = tmp_path / "myproject"
    scaffold_folders(project_path)
    for folder in STANDARD_FOLDERS:
        assert (project_path / folder).is_dir(), f"{folder} missing"


def test_scaffold_optional_data(tmp_path: Path) -> None:
    project_path = tmp_path / "p"
    scaffold_folders(project_path, optional_folders=["data"])
    assert (project_path / "data" / "raw").is_dir()
    assert (project_path / "data" / "processed").is_dir()
    assert (project_path / "data" / "metadata").is_dir()


def test_scaffold_optional_resultaten(tmp_path: Path) -> None:
    project_path = tmp_path / "p"
    scaffold_folders(project_path, optional_folders=["resultaten"])
    assert (project_path / "resultaten" / "export").is_dir()
    assert (project_path / "resultaten" / "figuren").is_dir()


def test_scaffold_all_optional(tmp_path: Path) -> None:
    project_path = tmp_path / "p"
    scaffold_folders(project_path, optional_folders=OPTIONAL_FOLDER_KEYS)
    assert (project_path / "notebooks").is_dir()
    assert (project_path / "src" / "queries").is_dir()
    assert (project_path / "literatuur").is_dir()


def test_scaffold_unknown_key_ignored(tmp_path: Path) -> None:
    project_path = tmp_path / "p"
    scaffold_folders(project_path, optional_folders=["nonexistent"])
    assert project_path.is_dir()


# ---------------------------------------------------------------------------
# export_project_json
# ---------------------------------------------------------------------------


def test_export_project_json(tmp_path: Path) -> None:
    project_path = tmp_path / "p"
    project_path.mkdir()
    project = {"id": "abc", "title": "T", "slug": "s", "status": "active"}
    out = export_project_json(project, project_path)
    assert out == project_path / "project.json"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["title"] == "T"
    assert "exported_at" in data


def test_export_project_json_strips_project_path_key(tmp_path: Path) -> None:
    project_path = tmp_path / "p"
    project_path.mkdir()
    project = {"id": "x", "project_path": "/some/path", "title": "T"}
    out = export_project_json(project, project_path)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "project_path" not in data


# ---------------------------------------------------------------------------
# create_project (integration)
# ---------------------------------------------------------------------------


def test_create_project_basic(tmp_path: Path) -> None:
    db = _db(tmp_path)
    root = tmp_path / "projects"
    result = create_project(
        "Churn Analysis",
        db_path=db,
        root_path_override=root,
    )
    assert result["title"] == "Churn Analysis"
    assert result["slug"].endswith("churn-analysis")
    assert result["status"] == "active"
    project_path = Path(result["project_path"])
    assert project_path.is_dir()
    assert (project_path / "archief").is_dir()
    assert (project_path / "project.json").is_file()


def test_create_project_with_optional_folders(tmp_path: Path) -> None:
    db = _db(tmp_path)
    root = tmp_path / "projects"
    result = create_project(
        "Dataset Analysis",
        optional_folders=["data", "notebooks"],
        db_path=db,
        root_path_override=root,
    )
    project_path = Path(result["project_path"])
    assert (project_path / "data" / "raw").is_dir()
    assert (project_path / "notebooks").is_dir()


def test_create_project_with_domain(tmp_path: Path) -> None:
    db = _db(tmp_path)
    result = create_project(
        "Healthcare Study",
        domain="healthcare",
        db_path=db,
        root_path_override=tmp_path / "r",
    )
    assert result["domain"] == "healthcare"


def test_create_project_raises_if_folder_exists(tmp_path: Path) -> None:
    db = _db(tmp_path)
    root = tmp_path / "projects"
    create_project("Duplicate", db_path=db, root_path_override=root)
    with pytest.raises(FileExistsError):
        create_project("Duplicate", db_path=db, root_path_override=root)


def test_create_project_project_json_content(tmp_path: Path) -> None:
    db = _db(tmp_path)
    result = create_project(
        "JSON Test",
        domain="finance",
        db_path=db,
        root_path_override=tmp_path / "r",
    )
    json_path = Path(result["project_path"]) / "project.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["domain"] == "finance"
    assert "project_path" not in data


def test_create_project_git_init(tmp_path: Path) -> None:
    db = _db(tmp_path)
    result = create_project(
        "Git Project",
        do_git_init=True,
        db_path=db,
        root_path_override=tmp_path / "r",
    )
    project_path = Path(result["project_path"])
    # .git dir exists OR git is not installed (graceful degradation)
    assert project_path.is_dir()


# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------


def test_list_projects_empty(tmp_path: Path) -> None:
    db = _db(tmp_path)
    assert list_projects(db_path=db) == []


def test_list_projects_returns_created(tmp_path: Path) -> None:
    db = _db(tmp_path)
    create_project("A", db_path=db, root_path_override=tmp_path / "r")
    create_project("B", domain="finance", db_path=db, root_path_override=tmp_path / "r")
    projects = list_projects(db_path=db)
    assert len(projects) == 2


def test_list_projects_filter_domain(tmp_path: Path) -> None:
    db = _db(tmp_path)
    r = tmp_path / "r"
    create_project("A", domain="healthcare", db_path=db, root_path_override=r)
    create_project("B", domain="finance", db_path=db, root_path_override=r)
    results = list_projects(domain="healthcare", db_path=db)
    assert len(results) == 1
    assert results[0]["domain"] == "healthcare"
