"""Tests for the search CLI command (argparse fallback)."""

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
    repo.create(
        title="Customer churn analysis",
        slug="2026-01-01-customer-churn-analysis",
        description="Predict attrition with logistic regression",
        domain="marketing",
        status="done",
    )
    repo.create(
        title="Hospital readmission study",
        slug="2026-02-15-hospital-readmission-study",
        domain="healthcare",
        status="active",
    )
    repo.create(
        title="Quarterly sales report",
        slug="2026-03-01-quarterly-sales-report",
        domain="finance",
        status="active",
    )

    tag_repo = TagRepository(conn)
    pt_repo = ProjectTagRepository(conn)
    ml_tag = tag_repo.create(name="machine-learning")
    p1 = repo.get_by_slug("2026-01-01-customer-churn-analysis")
    assert p1 is not None
    pt_repo.add(project_id=p1.id, tag_id=ml_tag.id)

    conn.close()
    return db_path


class TestSearchCLI:
    """Argparse search command tests."""

    def test_search_by_text(self, monkeypatch, tmp_path, capsys) -> None:
        _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr("sys.argv", ["datapm", "search", "churn"])
        main()
        out = capsys.readouterr().out
        assert "customer-churn-analysis" in out
        assert "Found 1 project" in out

    def test_search_by_domain_filter(self, monkeypatch, tmp_path, capsys) -> None:
        _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr("sys.argv", ["datapm", "search", "--domain", "healthcare"])
        main()
        out = capsys.readouterr().out
        assert "hospital-readmission-study" in out

    def test_search_by_status_filter(self, monkeypatch, tmp_path, capsys) -> None:
        _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr("sys.argv", ["datapm", "search", "--status", "active"])
        main()
        out = capsys.readouterr().out
        assert "Found 2 project" in out

    def test_search_by_tag_filter(self, monkeypatch, tmp_path, capsys) -> None:
        _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr(
            "sys.argv", ["datapm", "search", "--tag", "machine-learning"]
        )
        main()
        out = capsys.readouterr().out
        assert "customer-churn-analysis" in out

    def test_search_combined(self, monkeypatch, tmp_path, capsys) -> None:
        _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr(
            "sys.argv",
            ["datapm", "search", "churn", "--status", "done"],
        )
        main()
        out = capsys.readouterr().out
        assert "customer-churn-analysis" in out
        assert "Found 1 project" in out

    def test_search_no_results(self, monkeypatch, tmp_path, capsys) -> None:
        _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr("sys.argv", ["datapm", "search", "nonexistent"])
        main()
        out = capsys.readouterr().out
        assert "No projects found" in out

    def test_search_no_args_exits(self, monkeypatch, tmp_path) -> None:
        _patch_conn(monkeypatch, tmp_path)

        from data_project_manager.cli.fallback import main

        monkeypatch.setattr("sys.argv", ["datapm", "search"])
        with pytest.raises(SystemExit):
            main()
