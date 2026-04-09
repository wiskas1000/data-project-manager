"""Tests for core/project.py and core/templates.py."""

import json
from datetime import date
from pathlib import Path

import pytest

from data_project_manager.core.project import (
    create_project,
    export_project_json,
    generate_slug,
    git_init_project,
    list_projects,
    make_folder_name,
    scaffold_folders,
    slugify,
)
from data_project_manager.core.templates import (
    BASE_FOLDERS,
    BUILT_IN_ARCHETYPES,
    OPTIONAL_FOLDERS,
    get_archetype,
    resolve_folders,
)
from data_project_manager.db.schema import migrate

# ---------------------------------------------------------------------------
# Helpers / fixtures
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


@pytest.fixture()
def project_env(tmp_path: Path) -> tuple[Path, Path]:
    """Return ``(db_path, root_path)`` for integration tests."""
    return _db(tmp_path), tmp_path / "projects"


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
# scaffold_folders (new template system)
# ---------------------------------------------------------------------------


def test_scaffold_creates_base_folders(tmp_path: Path) -> None:
    project_path = tmp_path / "myproject"
    scaffold_folders(project_path)
    for key in BASE_FOLDERS:
        assert (project_path / key).is_dir(), f"{key} missing"


def test_scaffold_no_archief_by_default(tmp_path: Path) -> None:
    project_path = tmp_path / "myproject"
    scaffold_folders(project_path)
    assert not (project_path / "archief").exists()


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


def test_scaffold_notebooks_under_src(tmp_path: Path) -> None:
    project_path = tmp_path / "p"
    scaffold_folders(project_path, optional_folders=["src", "notebooks"])
    assert (project_path / "src" / "notebooks").is_dir()
    # notebooks should NOT be at top level
    assert not (project_path / "notebooks").exists()


def test_scaffold_queries_under_src(tmp_path: Path) -> None:
    project_path = tmp_path / "p"
    scaffold_folders(project_path, optional_folders=["src", "queries"])
    assert (project_path / "src" / "queries").is_dir()


def test_scaffold_src_alone(tmp_path: Path) -> None:
    project_path = tmp_path / "p"
    scaffold_folders(project_path, optional_folders=["src"])
    assert (project_path / "src").is_dir()
    # No children unless explicitly selected
    assert not (project_path / "src" / "notebooks").exists()
    assert not (project_path / "src" / "queries").exists()


def test_scaffold_literatuur(tmp_path: Path) -> None:
    project_path = tmp_path / "p"
    scaffold_folders(project_path, optional_folders=["literatuur"])
    assert (project_path / "literatuur").is_dir()


def test_scaffold_english_language(tmp_path: Path) -> None:
    project_path = tmp_path / "p"
    scaffold_folders(
        project_path,
        optional_folders=["data", "src", "notebooks", "literatuur", "resultaten"],
        language="en",
    )
    assert (project_path / "communication").is_dir()
    assert (project_path / "documents").is_dir()
    assert (project_path / "literature").is_dir()
    assert (project_path / "results" / "export").is_dir()
    assert (project_path / "results" / "figures").is_dir()
    assert (project_path / "src" / "notebooks").is_dir()


def test_scaffold_analysis_archetype_folders(tmp_path: Path) -> None:
    """Verify the analysis archetype creates the expected structure."""
    project_path = tmp_path / "p"
    arch = get_archetype("analysis")
    folders = resolve_folders(arch.folders)
    scaffold_folders(project_path, optional_folders=folders)
    assert (project_path / "communicatie").is_dir()
    assert (project_path / "documenten").is_dir()
    assert (project_path / "data" / "raw").is_dir()
    assert (project_path / "src" / "notebooks").is_dir()
    assert (project_path / "resultaten" / "export").is_dir()
    assert not (project_path / "literatuur").exists()


# ---------------------------------------------------------------------------
# templates: resolve_folders
# ---------------------------------------------------------------------------


def test_resolve_folders_notebooks_implies_src() -> None:
    result = resolve_folders(["notebooks"])
    assert "src" in result
    assert "notebooks" in result


def test_resolve_folders_queries_implies_src() -> None:
    result = resolve_folders(["queries"])
    assert "src" in result


def test_resolve_folders_remove_src_clears_children() -> None:
    result = resolve_folders(["data", "src", "notebooks"], remove=["src"])
    assert "src" not in result
    assert "notebooks" not in result
    assert "data" in result


def test_resolve_folders_add_and_remove() -> None:
    result = resolve_folders(
        ["data", "src", "notebooks"],
        add=["literatuur"],
        remove=["notebooks"],
    )
    assert "literatuur" in result
    assert "notebooks" not in result
    assert "src" in result  # still there, not removed


def test_resolve_folders_deduplicated() -> None:
    result = resolve_folders(["data", "data", "src"])
    assert result.count("data") == 1


def test_get_archetype_valid() -> None:
    arch = get_archetype("modeling")
    assert arch.label == "Modeling"
    assert "literatuur" in arch.folders


def test_get_archetype_invalid() -> None:
    with pytest.raises(ValueError, match="Unknown archetype"):
        get_archetype("nonexistent")


def test_all_archetypes_have_valid_folder_keys() -> None:
    for key, arch in BUILT_IN_ARCHETYPES.items():
        for f in arch.folders:
            assert f in OPTIONAL_FOLDERS, f"{key} has invalid folder {f}"


def test_minimal_archetype_has_no_folders() -> None:
    assert get_archetype("minimal").folders == []


def test_full_archetype_has_all_folders() -> None:
    assert set(get_archetype("full").folders) == set(OPTIONAL_FOLDERS)


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
# git_init_project (now targets src/)
# ---------------------------------------------------------------------------


def test_git_init_project_in_src(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    result = git_init_project(src_dir)
    if result:
        assert (src_dir / ".git").is_dir()
        assert (src_dir / ".gitignore").is_file()
        content = (src_dir / ".gitignore").read_text()
        assert "__pycache__/" in content


def test_git_init_returns_false_if_src_missing(tmp_path: Path) -> None:
    assert git_init_project(tmp_path / "nonexistent") is False


# ---------------------------------------------------------------------------
# create_project (integration)
# ---------------------------------------------------------------------------


def test_create_project_basic(project_env: tuple[Path, Path]) -> None:
    db, root = project_env
    result = create_project("Churn Analysis", db_path=db, root_path_override=root)
    assert result["title"] == "Churn Analysis"
    assert result["slug"].endswith("churn-analysis")
    assert result["status"] == "active"
    project_path = Path(result["project_path"])
    assert project_path.is_dir()
    assert (project_path / "communicatie").is_dir()
    assert (project_path / "documenten").is_dir()
    assert not (project_path / "archief").exists()
    assert (project_path / "project.json").is_file()


def test_create_project_default_template_is_analysis(
    project_env: tuple[Path, Path],
) -> None:
    db, root = project_env
    result = create_project("Default Template", db_path=db, root_path_override=root)
    assert result["template_used"] == "analysis"
    project_path = Path(result["project_path"])
    assert (project_path / "data" / "raw").is_dir()
    assert (project_path / "src" / "notebooks").is_dir()
    assert (project_path / "resultaten" / "export").is_dir()


def test_create_project_minimal_template(project_env: tuple[Path, Path]) -> None:
    db, root = project_env
    result = create_project(
        "Minimal Project", template_used="minimal", db_path=db, root_path_override=root
    )
    project_path = Path(result["project_path"])
    assert (project_path / "communicatie").is_dir()
    assert not (project_path / "data").exists()
    assert not (project_path / "src").exists()


def test_create_project_with_explicit_folders(
    project_env: tuple[Path, Path],
) -> None:
    db, root = project_env
    result = create_project(
        "Custom Folders",
        optional_folders=["data", "notebooks"],
        db_path=db,
        root_path_override=root,
    )
    project_path = Path(result["project_path"])
    assert (project_path / "data" / "raw").is_dir()
    assert (project_path / "src" / "notebooks").is_dir()


def test_create_project_with_domain(project_env: tuple[Path, Path]) -> None:
    db, root = project_env
    result = create_project(
        "Healthcare Study", domain="healthcare", db_path=db, root_path_override=root
    )
    assert result["domain"] == "healthcare"


def test_create_project_raises_if_folder_exists(
    project_env: tuple[Path, Path],
) -> None:
    db, root = project_env
    create_project("Duplicate", db_path=db, root_path_override=root)
    with pytest.raises(FileExistsError):
        create_project("Duplicate", db_path=db, root_path_override=root)


def test_create_project_project_json_content(
    project_env: tuple[Path, Path],
) -> None:
    db, root = project_env
    result = create_project(
        "JSON Test", domain="finance", db_path=db, root_path_override=root
    )
    json_path = Path(result["project_path"]) / "project.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["domain"] == "finance"
    assert "project_path" not in data


def test_create_project_git_init_in_src(project_env: tuple[Path, Path]) -> None:
    db, root = project_env
    result = create_project(
        "Git Project",
        do_git_init=True,
        optional_folders=["src"],
        db_path=db,
        root_path_override=root,
    )
    project_path = Path(result["project_path"])
    src_dir = project_path / "src"
    assert src_dir.is_dir()
    if result["has_git_repo"]:
        assert (src_dir / ".git").is_dir()
        assert (src_dir / ".gitignore").is_file()
        assert not (project_path / ".git").exists()


def test_create_project_git_no_src_sets_false(
    project_env: tuple[Path, Path],
) -> None:
    """Git init without src/ selected should set has_git_repo=False."""
    db, root = project_env
    result = create_project(
        "No Src Git",
        do_git_init=True,
        template_used="minimal",
        db_path=db,
        root_path_override=root,
    )
    assert result["has_git_repo"] == 0


def test_create_project_english_folders(project_env: tuple[Path, Path]) -> None:
    db, root = project_env
    result = create_project(
        "English Project",
        optional_folders=["data", "literatuur", "resultaten"],
        language="en",
        db_path=db,
        root_path_override=root,
    )
    project_path = Path(result["project_path"])
    assert (project_path / "communication").is_dir()
    assert (project_path / "documents").is_dir()
    assert (project_path / "literature").is_dir()
    assert (project_path / "results" / "figures").is_dir()


# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------


def test_list_projects_empty(project_env: tuple[Path, Path]) -> None:
    db, _root = project_env
    assert list_projects(db_path=db) == []


def test_list_projects_returns_created(project_env: tuple[Path, Path]) -> None:
    db, root = project_env
    create_project("A", db_path=db, root_path_override=root)
    create_project("B", domain="finance", db_path=db, root_path_override=root)
    assert len(list_projects(db_path=db)) == 2


def test_list_projects_filter_domain(project_env: tuple[Path, Path]) -> None:
    db, root = project_env
    create_project("A", domain="healthcare", db_path=db, root_path_override=root)
    create_project("B", domain="finance", db_path=db, root_path_override=root)
    results = list_projects(domain="healthcare", db_path=db)
    assert len(results) == 1
    assert results[0].domain == "healthcare"
