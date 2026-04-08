"""Tests for db/connection.py, db/schema.py, and db/repositories/project.py."""

import pytest
from helpers import fresh_conn

from data_project_manager.db.repositories.project import (
    ProjectRepository,
    ProjectRootRepository,
)
from data_project_manager.db.schema import SCHEMA_VERSION, get_schema_version, migrate

# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


def test_migrate_creates_schema_version_table() -> None:
    conn = fresh_conn()
    version = get_schema_version(conn)
    assert version == SCHEMA_VERSION


def test_migrate_is_idempotent() -> None:
    conn = fresh_conn()
    migrate(conn)  # second call — must not raise
    assert get_schema_version(conn) == SCHEMA_VERSION


def test_migrate_creates_project_table() -> None:
    conn = fresh_conn()
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='project'"
    ).fetchone()
    assert row is not None


def test_migrate_creates_project_root_table() -> None:
    conn = fresh_conn()
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='project_root'"
    ).fetchone()
    assert row is not None


def test_schema_version_is_2() -> None:
    assert SCHEMA_VERSION == 2


_MIGRATION_2_TABLES = [
    "person",
    "project_person",
    "tag",
    "project_tag",
    "data_file",
    "entity_type",
    "aggregation_level",
    "data_file_entity_type",
    "data_file_aggregation",
    "query",
    "deliverable",
    "deliverable_data_file",
    "request_question",
    "change_log",
]


@pytest.mark.parametrize("table_name", _MIGRATION_2_TABLES)
def test_migration_2_creates_table(table_name: str) -> None:
    conn = fresh_conn()
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    assert row is not None, f"Table {table_name} not created"


def test_seed_entity_types() -> None:
    conn = fresh_conn()
    rows = conn.execute("SELECT name FROM entity_type ORDER BY name").fetchall()
    names = [r["name"] for r in rows]
    assert "customers" in names
    assert "transactions" in names
    assert len(names) >= 6


def test_seed_aggregation_levels() -> None:
    conn = fresh_conn()
    rows = conn.execute("SELECT name FROM aggregation_level ORDER BY name").fetchall()
    names = [r["name"] for r in rows]
    assert "row" in names
    assert "daily" in names
    assert "monthly" in names
    assert len(names) >= 7


def test_migration_2_idempotent() -> None:
    conn = fresh_conn()
    migrate(conn)  # second call
    assert get_schema_version(conn) == SCHEMA_VERSION
    # Seed data should not duplicate (INSERT OR IGNORE)
    count = conn.execute("SELECT COUNT(*) FROM entity_type").fetchone()[0]
    assert count == 6


# ---------------------------------------------------------------------------
# ProjectRootRepository
# ---------------------------------------------------------------------------


def test_root_create_and_get() -> None:
    conn = fresh_conn()
    repo = ProjectRootRepository(conn)
    root = repo.create(name="work", absolute_path="/projects/work")
    assert root["name"] == "work"
    assert root["absolute_path"] == "/projects/work"
    assert root["is_default"] == 0

    fetched = repo.get(root["id"])
    assert fetched == root


def test_root_get_by_name() -> None:
    conn = fresh_conn()
    repo = ProjectRootRepository(conn)
    repo.create(name="work", absolute_path="/projects/work")
    root = repo.get_by_name("work")
    assert root is not None
    assert root["name"] == "work"


def test_root_get_by_name_missing() -> None:
    conn = fresh_conn()
    assert ProjectRootRepository(conn).get_by_name("nope") is None


def test_root_list() -> None:
    conn = fresh_conn()
    repo = ProjectRootRepository(conn)
    repo.create(name="personal", absolute_path="/projects/personal")
    repo.create(name="work", absolute_path="/projects/work")
    roots = repo.list()
    assert len(roots) == 2
    assert roots[0]["name"] == "personal"  # ordered by name


def test_root_set_default() -> None:
    conn = fresh_conn()
    repo = ProjectRootRepository(conn)
    r1 = repo.create(name="work", absolute_path="/projects/work", is_default=True)
    r2 = repo.create(name="personal", absolute_path="/projects/personal")
    repo.set_default(r2["id"])
    assert repo.get(r1["id"])["is_default"] == 0
    assert repo.get(r2["id"])["is_default"] == 1


def test_root_get_default_none() -> None:
    conn = fresh_conn()
    assert ProjectRootRepository(conn).get_default() is None


def test_root_get_default() -> None:
    conn = fresh_conn()
    repo = ProjectRootRepository(conn)
    root = repo.create(name="work", absolute_path="/p/work", is_default=True)
    assert repo.get_default()["id"] == root["id"]


# ---------------------------------------------------------------------------
# ProjectRepository
# ---------------------------------------------------------------------------


def test_project_create_and_get() -> None:
    conn = fresh_conn()
    repo = ProjectRepository(conn)
    p = repo.create(title="Churn analysis", slug="2026-04-06-churn-analysis")
    assert p["title"] == "Churn analysis"
    assert p["slug"] == "2026-04-06-churn-analysis"
    assert p["status"] == "active"
    assert p["is_adhoc"] == 0

    fetched = repo.get(p["id"])
    assert fetched == p


def test_project_get_by_slug() -> None:
    conn = fresh_conn()
    repo = ProjectRepository(conn)
    repo.create(title="T", slug="2026-01-01-t")
    p = repo.get_by_slug("2026-01-01-t")
    assert p is not None
    assert p["title"] == "T"


def test_project_get_missing() -> None:
    conn = fresh_conn()
    assert ProjectRepository(conn).get("nonexistent") is None


def test_project_create_invalid_status() -> None:
    conn = fresh_conn()
    with pytest.raises(ValueError, match="Invalid status"):
        ProjectRepository(conn).create(title="T", slug="s", status="unknown")


def test_project_list_all() -> None:
    conn = fresh_conn()
    repo = ProjectRepository(conn)
    repo.create(title="A", slug="2026-01-01-a")
    repo.create(title="B", slug="2026-01-02-b")
    assert len(repo.list()) == 2


def test_project_list_filter_status() -> None:
    conn = fresh_conn()
    repo = ProjectRepository(conn)
    repo.create(title="A", slug="2026-01-01-a", status="active")
    repo.create(title="B", slug="2026-01-02-b", status="done")
    assert len(repo.list(status="active")) == 1
    assert len(repo.list(status="done")) == 1


def test_project_list_filter_domain() -> None:
    conn = fresh_conn()
    repo = ProjectRepository(conn)
    repo.create(title="A", slug="s-a", domain="healthcare")
    repo.create(title="B", slug="s-b", domain="finance")
    assert repo.list(domain="healthcare")[0]["title"] == "A"


def test_project_update_status() -> None:
    conn = fresh_conn()
    repo = ProjectRepository(conn)
    p = repo.create(title="T", slug="s")
    updated = repo.update(p["id"], status="done")
    assert updated["status"] == "done"
    assert updated["updated_at"] > p["updated_at"]


def test_project_update_invalid_status() -> None:
    conn = fresh_conn()
    repo = ProjectRepository(conn)
    p = repo.create(title="T", slug="s")
    with pytest.raises(ValueError, match="Invalid status"):
        repo.update(p["id"], status="bad")


def test_project_update_missing_id() -> None:
    conn = fresh_conn()
    result = ProjectRepository(conn).update("nonexistent", status="done")
    assert result is None


def test_project_update_no_fields() -> None:
    conn = fresh_conn()
    repo = ProjectRepository(conn)
    p = repo.create(title="T", slug="s")
    result = repo.update(p["id"])
    assert result == repo.get(p["id"])


def test_project_create_duplicate_slug_raises_value_error() -> None:
    conn = fresh_conn()
    repo = ProjectRepository(conn)
    repo.create(title="T", slug="2026-04-07-duplicate")
    with pytest.raises(ValueError, match="already exists"):
        repo.create(title="T2", slug="2026-04-07-duplicate")


def test_project_update_rejects_immutable_columns() -> None:
    conn = fresh_conn()
    repo = ProjectRepository(conn)
    p = repo.create(title="T", slug="s")
    with pytest.raises(ValueError, match="immutable or unknown"):
        repo.update(p["id"], id="new-id")
    with pytest.raises(ValueError, match="immutable or unknown"):
        repo.update(p["id"], created_at="2020-01-01")
    with pytest.raises(ValueError, match="immutable or unknown"):
        repo.update(p["id"], slug="new-slug")


def test_project_update_rejects_unknown_columns() -> None:
    conn = fresh_conn()
    repo = ProjectRepository(conn)
    p = repo.create(title="T", slug="s")
    with pytest.raises(ValueError, match="immutable or unknown"):
        repo.update(p["id"], nonexistent_field="value")


def test_project_with_root_fk() -> None:
    conn = fresh_conn()
    root_repo = ProjectRootRepository(conn)
    proj_repo = ProjectRepository(conn)
    root = root_repo.create(name="work", absolute_path="/p/work")
    p = proj_repo.create(title="T", slug="s", root_id=root["id"])
    assert p["root_id"] == root["id"]
    assert len(proj_repo.list(root_id=root["id"])) == 1
