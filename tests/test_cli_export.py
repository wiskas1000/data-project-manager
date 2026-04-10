"""Tests for the export CLI command (argparse fallback)."""

import json

import pytest

from data_project_manager.db.connection import get_connection
from data_project_manager.db.repositories.project import ProjectRepository
from data_project_manager.db.repositories.tag import ProjectTagRepository, TagRepository


def _patch_conn(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Redirect get_connection to a temp file DB and seed data."""
    import data_project_manager.db.connection as _conn_mod

    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(
        _conn_mod,
        "get_connection",
        lambda _p=None: get_connection(db_path),
    )

    conn = get_connection(db_path)
    repo = ProjectRepository(conn)
    project = repo.create(
        title="Churn analysis",
        slug="2026-01-01-churn-analysis",
        description="Predict customer attrition",
        domain="marketing",
    )
    tag_repo = TagRepository(conn)
    pt_repo = ProjectTagRepository(conn)
    ml_tag = tag_repo.create(name="machine-learning")
    pt_repo.add(project_id=project.id, tag_id=ml_tag.id)
    conn.close()
    return db_path


class TestExportCLI:
    """Argparse export command tests."""

    def test_export_single_project(self, monkeypatch, tmp_path, capsys) -> None:
        _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr(
            "sys.argv", ["datapm", "export", "2026-01-01-churn-analysis"]
        )
        main()
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["slug"] == "2026-01-01-churn-analysis"
        assert len(data["tags"]) == 1

    def test_export_all(self, monkeypatch, tmp_path, capsys) -> None:
        _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr("sys.argv", ["datapm", "export", "--all"])
        main()
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["count"] == 1
        assert len(data["projects"]) == 1

    def test_export_no_slug_defaults_to_all(
        self, monkeypatch, tmp_path, capsys
    ) -> None:
        _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr("sys.argv", ["datapm", "export"])
        main()
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "count" in data

    def test_export_not_found(self, monkeypatch, tmp_path) -> None:
        _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr("sys.argv", ["datapm", "export", "nonexistent"])
        with pytest.raises(SystemExit):
            main()

    def test_export_compact(self, monkeypatch, tmp_path, capsys) -> None:
        _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr(
            "sys.argv",
            ["datapm", "export", "2026-01-01-churn-analysis", "--compact"],
        )
        main()
        out = capsys.readouterr().out.strip()
        # Compact JSON has no newlines inside the object
        assert "\n" not in out
        data = json.loads(out)
        assert data["slug"] == "2026-01-01-churn-analysis"

    def test_export_redact_single(self, monkeypatch, tmp_path, capsys) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)

        # Add a person so --redact has PII to strip
        from data_project_manager.db.repositories.person import (
            PersonRepository,
            ProjectPersonRepository,
        )

        conn = get_connection(db_path)
        person_repo = PersonRepository(conn)
        pp_repo = ProjectPersonRepository(conn)
        project_repo = ProjectRepository(conn)
        project = project_repo.get_by_slug("2026-01-01-churn-analysis")
        person = person_repo.create(first_name="Alice", last_name="Smith")
        pp_repo.add(project_id=project.id, person_id=person.id, role="analyst")
        conn.close()

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr(
            "sys.argv",
            ["datapm", "export", "2026-01-01-churn-analysis", "--redact"],
        )
        main()
        out = capsys.readouterr().out
        data = json.loads(out)
        person_data = data["people"][0]
        assert person_data["first_name"] == "[REDACTED]"
        assert person_data["last_name"] == "[REDACTED]"
        assert person_data["role"] == "analyst"

    def test_export_redact_all(self, monkeypatch, tmp_path, capsys) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.db.repositories.person import (
            PersonRepository,
            ProjectPersonRepository,
        )

        conn = get_connection(db_path)
        person_repo = PersonRepository(conn)
        pp_repo = ProjectPersonRepository(conn)
        project_repo = ProjectRepository(conn)
        project = project_repo.get_by_slug("2026-01-01-churn-analysis")
        person = person_repo.create(first_name="Bob", last_name="Jones")
        pp_repo.add(project_id=project.id, person_id=person.id, role="lead")
        conn.close()

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr("sys.argv", ["datapm", "export", "--all", "--redact"])
        main()
        out = capsys.readouterr().out
        data = json.loads(out)
        churn = next(
            p for p in data["projects"] if p["slug"] == "2026-01-01-churn-analysis"
        )
        assert churn["people"][0]["first_name"] == "[REDACTED]"

    def test_export_to_file(self, monkeypatch, tmp_path, capsys) -> None:
        _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.cli.fallback import main

        out_file = str(tmp_path / "export.json")
        monkeypatch.setattr(
            "sys.argv",
            ["datapm", "export", "2026-01-01-churn-analysis", "--output", out_file],
        )
        main()

        from pathlib import Path

        content = Path(out_file).read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["slug"] == "2026-01-01-churn-analysis"

        out = capsys.readouterr().out
        assert "Exported to" in out
