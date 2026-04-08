"""Tests for db/repositories/person.py and db/repositories/tag.py."""

import sqlite3

import pytest

from data_project_manager.db.repositories.person import (
    PersonRepository,
    ProjectPersonRepository,
)
from data_project_manager.db.repositories.project import (
    ProjectRepository,
)
from data_project_manager.db.repositories.tag import (
    ProjectTagRepository,
    TagRepository,
)
from data_project_manager.db.schema import migrate


def fresh_conn() -> sqlite3.Connection:
    """Return a migrated in-memory connection."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn)
    return conn


def _make_project(conn: sqlite3.Connection, title: str = "Test") -> dict:
    """Create a minimal project and return it."""
    return ProjectRepository(conn).create(
        title=title, slug=f"2026-01-01-{title.lower().replace(' ', '-')}"
    )


# ---------------------------------------------------------------------------
# PersonRepository
# ---------------------------------------------------------------------------


class TestPersonRepository:
    def test_create_and_get(self) -> None:
        conn = fresh_conn()
        repo = PersonRepository(conn)
        p = repo.create(first_name="Jane", last_name="Doe")
        assert p["first_name"] == "Jane"
        assert p["last_name"] == "Doe"
        assert p["is_current"] == 1
        assert p["valid_to"] is None
        assert repo.get(p["id"]) == p

    def test_create_with_all_fields(self) -> None:
        conn = fresh_conn()
        repo = PersonRepository(conn)
        p = repo.create(
            first_name="John",
            last_name="Smith",
            email="john@example.com",
            function_title="Data Scientist",
            department="Analytics",
            valid_from="2026-01-01",
        )
        assert p["email"] == "john@example.com"
        assert p["function_title"] == "Data Scientist"
        assert p["department"] == "Analytics"
        assert p["valid_from"] == "2026-01-01"

    def test_get_missing(self) -> None:
        conn = fresh_conn()
        assert PersonRepository(conn).get("nonexistent") is None

    def test_get_current_by_email(self) -> None:
        conn = fresh_conn()
        repo = PersonRepository(conn)
        repo.create(first_name="Jane", last_name="Doe", email="jane@example.com")
        result = repo.get_current_by_email("jane@example.com")
        assert result is not None
        assert result["first_name"] == "Jane"

    def test_get_current_by_email_missing(self) -> None:
        conn = fresh_conn()
        assert PersonRepository(conn).get_current_by_email("x@x.com") is None

    def test_list_current_only(self) -> None:
        conn = fresh_conn()
        repo = PersonRepository(conn)
        p = repo.create(first_name="A", last_name="B")
        repo.create_new_version(p["id"], department="New Dept")
        current = repo.list(current_only=True)
        assert len(current) == 1
        assert current[0]["department"] == "New Dept"

    def test_list_all_versions(self) -> None:
        conn = fresh_conn()
        repo = PersonRepository(conn)
        p = repo.create(first_name="A", last_name="B")
        repo.create_new_version(p["id"], department="New Dept")
        all_versions = repo.list(current_only=False)
        assert len(all_versions) == 2

    def test_list_ordered_by_last_name(self) -> None:
        conn = fresh_conn()
        repo = PersonRepository(conn)
        repo.create(first_name="Z", last_name="Zebra")
        repo.create(first_name="A", last_name="Alpha")
        persons = repo.list()
        assert persons[0]["last_name"] == "Alpha"
        assert persons[1]["last_name"] == "Zebra"

    def test_create_new_version(self) -> None:
        conn = fresh_conn()
        repo = PersonRepository(conn)
        v1 = repo.create(
            first_name="Jane",
            last_name="Doe",
            department="Analytics",
        )
        v2 = repo.create_new_version(v1["id"], department="Data Science")

        # New version has updated department
        assert v2["department"] == "Data Science"
        assert v2["is_current"] == 1
        assert v2["valid_to"] is None
        assert v2["id"] != v1["id"]

        # Old version is closed
        old = repo.get(v1["id"])
        assert old["is_current"] == 0
        assert old["valid_to"] is not None

        # Other fields carried forward
        assert v2["first_name"] == "Jane"
        assert v2["last_name"] == "Doe"

    def test_create_new_version_carries_forward_fields(self) -> None:
        conn = fresh_conn()
        repo = PersonRepository(conn)
        v1 = repo.create(
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            function_title="Analyst",
            department="Analytics",
        )
        v2 = repo.create_new_version(v1["id"], function_title="Senior Analyst")
        assert v2["email"] == "jane@example.com"
        assert v2["department"] == "Analytics"
        assert v2["function_title"] == "Senior Analyst"

    def test_create_new_version_nonexistent_raises(self) -> None:
        conn = fresh_conn()
        with pytest.raises(ValueError, match="not found"):
            PersonRepository(conn).create_new_version("fake-id")

    def test_create_new_version_non_current_raises(self) -> None:
        conn = fresh_conn()
        repo = PersonRepository(conn)
        v1 = repo.create(first_name="A", last_name="B")
        repo.create_new_version(v1["id"], department="New")
        with pytest.raises(ValueError, match="not the current version"):
            repo.create_new_version(v1["id"], department="Another")


# ---------------------------------------------------------------------------
# ProjectPersonRepository
# ---------------------------------------------------------------------------


class TestProjectPersonRepository:
    def test_add_and_list_for_project(self) -> None:
        conn = fresh_conn()
        project = _make_project(conn)
        person = PersonRepository(conn).create(first_name="Jane", last_name="Doe")
        pp = ProjectPersonRepository(conn)
        pp.add(
            project_id=project["id"],
            person_id=person["id"],
            role="requestor",
        )
        entries = pp.list_for_project(project["id"])
        assert len(entries) == 1
        assert entries[0]["role"] == "requestor"
        assert entries[0]["first_name"] == "Jane"

    def test_add_duplicate_ignored(self) -> None:
        conn = fresh_conn()
        project = _make_project(conn)
        person = PersonRepository(conn).create(first_name="A", last_name="B")
        pp = ProjectPersonRepository(conn)
        pp.add(
            project_id=project["id"],
            person_id=person["id"],
            role="reviewer",
        )
        pp.add(
            project_id=project["id"],
            person_id=person["id"],
            role="reviewer",
        )
        assert len(pp.list_for_project(project["id"])) == 1

    def test_same_person_multiple_roles(self) -> None:
        conn = fresh_conn()
        project = _make_project(conn)
        person = PersonRepository(conn).create(first_name="A", last_name="B")
        pp = ProjectPersonRepository(conn)
        pp.add(
            project_id=project["id"],
            person_id=person["id"],
            role="requestor",
        )
        pp.add(
            project_id=project["id"],
            person_id=person["id"],
            role="reviewer",
        )
        assert len(pp.list_for_project(project["id"])) == 2

    def test_remove(self) -> None:
        conn = fresh_conn()
        project = _make_project(conn)
        person = PersonRepository(conn).create(first_name="A", last_name="B")
        pp = ProjectPersonRepository(conn)
        pp.add(
            project_id=project["id"],
            person_id=person["id"],
            role="requestor",
        )
        pp.remove(
            project_id=project["id"],
            person_id=person["id"],
            role="requestor",
        )
        assert len(pp.list_for_project(project["id"])) == 0

    def test_list_for_person(self) -> None:
        conn = fresh_conn()
        p1 = _make_project(conn, "Project A")
        p2 = _make_project(conn, "Project B")
        person = PersonRepository(conn).create(first_name="A", last_name="B")
        pp = ProjectPersonRepository(conn)
        pp.add(project_id=p1["id"], person_id=person["id"], role="requestor")
        pp.add(project_id=p2["id"], person_id=person["id"], role="reviewer")
        entries = pp.list_for_person(person["id"])
        assert len(entries) == 2


# ---------------------------------------------------------------------------
# TagRepository
# ---------------------------------------------------------------------------


class TestTagRepository:
    def test_create_and_get(self) -> None:
        conn = fresh_conn()
        repo = TagRepository(conn)
        tag = repo.create(name="machine-learning")
        assert tag["name"] == "machine-learning"
        assert repo.get(tag["id"]) == tag

    def test_create_normalises_name(self) -> None:
        conn = fresh_conn()
        repo = TagRepository(conn)
        tag = repo.create(name="  Machine-Learning  ")
        assert tag["name"] == "machine-learning"

    def test_create_with_category(self) -> None:
        conn = fresh_conn()
        tag = TagRepository(conn).create(name="logistic-regression", category="method")
        assert tag["category"] == "method"

    def test_create_duplicate_returns_existing(self) -> None:
        conn = fresh_conn()
        repo = TagRepository(conn)
        t1 = repo.create(name="ml")
        t2 = repo.create(name="ML")  # same after normalisation
        assert t1["id"] == t2["id"]

    def test_get_by_name(self) -> None:
        conn = fresh_conn()
        repo = TagRepository(conn)
        repo.create(name="churn")
        assert repo.get_by_name("churn") is not None
        assert repo.get_by_name("CHURN") is not None  # case-insensitive
        assert repo.get_by_name("nonexistent") is None

    def test_list(self) -> None:
        conn = fresh_conn()
        repo = TagRepository(conn)
        repo.create(name="zebra")
        repo.create(name="alpha")
        tags = repo.list()
        assert tags[0]["name"] == "alpha"
        assert tags[1]["name"] == "zebra"

    def test_list_filter_category(self) -> None:
        conn = fresh_conn()
        repo = TagRepository(conn)
        repo.create(name="lr", category="method")
        repo.create(name="healthcare", category="domain")
        assert len(repo.list(category="method")) == 1
        assert len(repo.list(category="domain")) == 1


# ---------------------------------------------------------------------------
# ProjectTagRepository
# ---------------------------------------------------------------------------


class TestProjectTagRepository:
    def test_add_and_list_for_project(self) -> None:
        conn = fresh_conn()
        project = _make_project(conn)
        tag = TagRepository(conn).create(name="ml")
        pt = ProjectTagRepository(conn)
        pt.add(project_id=project["id"], tag_id=tag["id"])
        tags = pt.list_for_project(project["id"])
        assert len(tags) == 1
        assert tags[0]["name"] == "ml"

    def test_add_duplicate_ignored(self) -> None:
        conn = fresh_conn()
        project = _make_project(conn)
        tag = TagRepository(conn).create(name="ml")
        pt = ProjectTagRepository(conn)
        pt.add(project_id=project["id"], tag_id=tag["id"])
        pt.add(project_id=project["id"], tag_id=tag["id"])
        assert len(pt.list_for_project(project["id"])) == 1

    def test_remove(self) -> None:
        conn = fresh_conn()
        project = _make_project(conn)
        tag = TagRepository(conn).create(name="ml")
        pt = ProjectTagRepository(conn)
        pt.add(project_id=project["id"], tag_id=tag["id"])
        pt.remove(project_id=project["id"], tag_id=tag["id"])
        assert len(pt.list_for_project(project["id"])) == 0

    def test_list_projects_for_tag(self) -> None:
        conn = fresh_conn()
        p1 = _make_project(conn, "A")
        p2 = _make_project(conn, "B")
        tag = TagRepository(conn).create(name="shared-tag")
        pt = ProjectTagRepository(conn)
        pt.add(project_id=p1["id"], tag_id=tag["id"])
        pt.add(project_id=p2["id"], tag_id=tag["id"])
        project_ids = pt.list_projects_for_tag(tag["id"])
        assert len(project_ids) == 2
