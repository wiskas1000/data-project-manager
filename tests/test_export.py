"""Tests for core/export.py — JSON export of project metadata."""

import json

import pytest
from helpers import fresh_conn

from data_project_manager.core.export import (
    _build_all_export,
    _build_project_export,
)
from data_project_manager.db.repositories.data_file import DataFileRepository
from data_project_manager.db.repositories.deliverable import DeliverableRepository
from data_project_manager.db.repositories.person import (
    PersonRepository,
    ProjectPersonRepository,
)
from data_project_manager.db.repositories.project import ProjectRepository
from data_project_manager.db.repositories.question import RequestQuestionRepository
from data_project_manager.db.repositories.tag import ProjectTagRepository, TagRepository


@pytest.fixture()
def export_conn():
    """Return a migrated connection with a project and relationships."""
    conn = fresh_conn()
    repo = ProjectRepository(conn)

    project = repo.create(
        title="Churn analysis",
        slug="2026-01-01-churn-analysis",
        description="Predict customer attrition",
        domain="marketing",
    )

    # Tag
    tag_repo = TagRepository(conn)
    pt_repo = ProjectTagRepository(conn)
    ml_tag = tag_repo.create(name="machine-learning")
    pt_repo.add(project_id=project.id, tag_id=ml_tag.id)

    # Person
    person_repo = PersonRepository(conn)
    pp_repo = ProjectPersonRepository(conn)
    person = person_repo.create(first_name="Alice", last_name="Smith")
    pp_repo.add(project_id=project.id, person_id=person.id, role="analyst")

    # Data file
    df_repo = DataFileRepository(conn)
    df_repo.create(
        project_id=project.id,
        file_path="data/raw/customers.csv",
        sensitivity="internal",
    )

    # Deliverable
    del_repo = DeliverableRepository(conn)
    del_repo.create(
        project_id=project.id,
        type="report",
        file_path="output/report.pdf",
    )

    # Question
    q_repo = RequestQuestionRepository(conn)
    q_repo.create(
        project_id=project.id,
        question_text="What is the churn rate?",
    )

    # Second project (no relationships)
    repo.create(
        title="Empty project",
        slug="2026-02-01-empty-project",
    )

    return conn


class TestExportProject:
    """Export a single project."""

    def test_export_found(self, export_conn) -> None:
        data = _build_project_export(export_conn, "2026-01-01-churn-analysis")
        assert data is not None
        assert data["slug"] == "2026-01-01-churn-analysis"
        assert data["title"] == "Churn analysis"
        assert data["domain"] == "marketing"

    def test_export_not_found(self, export_conn) -> None:
        data = _build_project_export(export_conn, "nonexistent")
        assert data is None

    def test_export_includes_tags(self, export_conn) -> None:
        data = _build_project_export(export_conn, "2026-01-01-churn-analysis")
        assert data is not None
        assert len(data["tags"]) == 1
        assert data["tags"][0]["name"] == "machine-learning"

    def test_export_includes_people(self, export_conn) -> None:
        data = _build_project_export(export_conn, "2026-01-01-churn-analysis")
        assert data is not None
        assert len(data["people"]) == 1
        assert data["people"][0]["first_name"] == "Alice"
        assert data["people"][0]["role"] == "analyst"

    def test_export_includes_data_files(self, export_conn) -> None:
        data = _build_project_export(export_conn, "2026-01-01-churn-analysis")
        assert data is not None
        assert len(data["data_files"]) == 1
        assert data["data_files"][0]["file_path"] == "data/raw/customers.csv"

    def test_export_includes_deliverables(self, export_conn) -> None:
        data = _build_project_export(export_conn, "2026-01-01-churn-analysis")
        assert data is not None
        assert len(data["deliverables"]) == 1
        assert data["deliverables"][0]["type"] == "report"

    def test_export_includes_questions(self, export_conn) -> None:
        data = _build_project_export(export_conn, "2026-01-01-churn-analysis")
        assert data is not None
        assert len(data["questions"]) == 1
        assert data["questions"][0]["question_text"] == "What is the churn rate?"

    def test_export_includes_exported_at(self, export_conn) -> None:
        data = _build_project_export(export_conn, "2026-01-01-churn-analysis")
        assert data is not None
        assert "exported_at" in data

    def test_export_empty_relationships(self, export_conn) -> None:
        data = _build_project_export(export_conn, "2026-02-01-empty-project")
        assert data is not None
        assert data["tags"] == []
        assert data["people"] == []
        assert data["data_files"] == []
        assert data["deliverables"] == []
        assert data["questions"] == []

    def test_export_is_json_serializable(self, export_conn) -> None:
        data = _build_project_export(export_conn, "2026-01-01-churn-analysis")
        assert data is not None
        output = json.dumps(data, default=str)
        parsed = json.loads(output)
        assert parsed["slug"] == "2026-01-01-churn-analysis"


class TestExportAll:
    """Export all projects."""

    def test_export_all_count(self, export_conn) -> None:
        data = _build_all_export(export_conn)
        assert data["count"] == 2

    def test_export_all_structure(self, export_conn) -> None:
        data = _build_all_export(export_conn)
        assert "exported_at" in data
        assert "projects" in data
        assert isinstance(data["projects"], list)

    def test_export_all_includes_relationships(self, export_conn) -> None:
        data = _build_all_export(export_conn)
        slugs = {p["slug"] for p in data["projects"]}
        assert "2026-01-01-churn-analysis" in slugs
        churn = next(p for p in data["projects"] if p["slug"].startswith("2026-01-01"))
        assert len(churn["tags"]) == 1

    def test_export_all_json_serializable(self, export_conn) -> None:
        data = _build_all_export(export_conn)
        output = json.dumps(data, default=str)
        parsed = json.loads(output)
        assert parsed["count"] == 2
