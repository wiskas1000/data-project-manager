"""Tests for the Typer-based enhanced CLI (cli/app.py)."""

import json

from typer.testing import CliRunner

from data_project_manager.db.connection import get_connection
from data_project_manager.db.repositories.changelog import ChangeLogRepository
from data_project_manager.db.repositories.person import (
    PersonRepository,
    ProjectPersonRepository,
)
from data_project_manager.db.repositories.project import ProjectRepository
from data_project_manager.db.repositories.tag import ProjectTagRepository, TagRepository

runner = CliRunner()


def _patch_conn(monkeypatch, tmp_path):
    """Redirect get_connection to a temp file DB."""
    import data_project_manager.db.connection as _conn_mod

    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(
        _conn_mod,
        "get_connection",
        lambda _p=None: get_connection(db_path),
    )
    return db_path


def _seed_projects(db_path: str):
    """Create test projects in the database."""
    conn = get_connection(db_path)
    repo = ProjectRepository(conn)
    p1 = repo.create(
        title="Customer churn analysis",
        slug="2026-01-01-customer-churn-analysis",
        description="Predict attrition with logistic regression",
        domain="marketing",
        status="done",
        has_git_repo=True,
        template_used="analysis",
    )
    p2 = repo.create(
        title="Hospital readmission study",
        slug="2026-02-15-hospital-readmission-study",
        domain="healthcare",
        status="active",
    )
    p3 = repo.create(
        title="Quarterly sales report",
        slug="2026-03-01-quarterly-sales-report",
        domain="finance",
        status="active",
    )

    # Add tags
    tag_repo = TagRepository(conn)
    pt_repo = ProjectTagRepository(conn)
    ml_tag = tag_repo.create(name="machine-learning")
    pt_repo.add(project_id=p1.id, tag_id=ml_tag.id)

    # Add people
    person_repo = PersonRepository(conn)
    pp_repo = ProjectPersonRepository(conn)
    person = person_repo.create(first_name="Alice", last_name="Smith")
    pp_repo.add(project_id=p1.id, person_id=person.id, role="lead")

    # Add changelog entry
    changelog = ChangeLogRepository(conn)
    changelog.log(
        entity_type="project",
        entity_id=p1.id,
        field_name="status",
        old_value="active",
        new_value="done",
    )

    conn.close()
    return p1, p2, p3


# ---------------------------------------------------------------------------
# list command
# ---------------------------------------------------------------------------


class TestListCommand:
    def test_list_all(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "customer-churn-analysis" in result.output
        assert "hospital-readmission-study" in result.output

    def test_list_filter_status(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["list", "--status", "done"])
        assert result.exit_code == 0
        assert "customer-churn-analysis" in result.output
        assert "hospital-readmission-study" not in result.output

    def test_list_filter_domain(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["list", "--domain", "healthcare"])
        assert result.exit_code == 0
        assert "hospital-readmission-study" in result.output

    def test_list_empty(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        _patch_conn(monkeypatch, tmp_path)

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No projects found" in result.output


# ---------------------------------------------------------------------------
# info command
# ---------------------------------------------------------------------------


class TestInfoCommand:
    def test_info_shows_details(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["info", "2026-01-01-customer-churn-analysis"])
        assert result.exit_code == 0
        assert "Customer churn analysis" in result.output
        assert "marketing" in result.output
        assert "done" in result.output

    def test_info_shows_tags(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["info", "2026-01-01-customer-churn-analysis"])
        assert "machine-learning" in result.output

    def test_info_shows_people(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["info", "2026-01-01-customer-churn-analysis"])
        assert "Alice" in result.output
        assert "Smith" in result.output

    def test_info_shows_changelog(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["info", "2026-01-01-customer-churn-analysis"])
        assert "status" in result.output

    def test_info_not_found(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        _patch_conn(monkeypatch, tmp_path)

        result = runner.invoke(app, ["info", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output


# ---------------------------------------------------------------------------
# project update command
# ---------------------------------------------------------------------------


class TestProjectUpdateCommand:
    def test_update_status(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(
            app,
            [
                "project",
                "update",
                "2026-02-15-hospital-readmission-study",
                "--status",
                "done",
            ],
        )
        assert result.exit_code == 0
        assert "Updated" in result.output

    def test_update_domain(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(
            app,
            [
                "project",
                "update",
                "2026-02-15-hospital-readmission-study",
                "--domain",
                "medical",
            ],
        )
        assert result.exit_code == 0
        assert "domain" in result.output

    def test_update_add_tag(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(
            app,
            [
                "project",
                "update",
                "2026-02-15-hospital-readmission-study",
                "--tag",
                "urgent",
            ],
        )
        assert result.exit_code == 0
        assert "tag added" in result.output

    def test_update_remove_tag(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        # First add a tag
        runner.invoke(
            app,
            [
                "project",
                "update",
                "2026-02-15-hospital-readmission-study",
                "--tag",
                "temp",
            ],
        )
        result = runner.invoke(
            app,
            [
                "project",
                "update",
                "2026-02-15-hospital-readmission-study",
                "--remove-tag",
                "temp",
            ],
        )
        assert result.exit_code == 0
        assert "tag removed" in result.output

    def test_update_nothing(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(
            app,
            ["project", "update", "2026-02-15-hospital-readmission-study"],
        )
        assert result.exit_code == 0
        assert "Nothing to update" in result.output

    def test_update_invalid_status(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(
            app,
            [
                "project",
                "update",
                "2026-02-15-hospital-readmission-study",
                "--status",
                "invalid",
            ],
        )
        assert result.exit_code == 1

    def test_update_not_found(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        _patch_conn(monkeypatch, tmp_path)

        result = runner.invoke(
            app, ["project", "update", "nonexistent", "--status", "done"]
        )
        assert result.exit_code == 1
        assert "not found" in result.output


# ---------------------------------------------------------------------------
# search command
# ---------------------------------------------------------------------------


class TestSearchCommand:
    def test_search_text(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["search", "churn"])
        assert result.exit_code == 0
        assert "customer-churn-analysis" in result.output
        assert "1" in result.output  # "Found 1 project"

    def test_search_by_domain(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["search", "--domain", "healthcare"])
        assert result.exit_code == 0
        assert "hospital-readmission-study" in result.output

    def test_search_by_status(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["search", "--status", "active"])
        assert result.exit_code == 0
        assert "2" in result.output  # "Found 2 project(s)"

    def test_search_by_tag(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["search", "--tag", "machine-learning"])
        assert result.exit_code == 0
        assert "customer-churn-analysis" in result.output

    def test_search_no_results(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["search", "xyznonexistent"])
        assert result.exit_code == 0
        assert "No projects found" in result.output

    def test_search_no_args(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        _patch_conn(monkeypatch, tmp_path)

        result = runner.invoke(app, ["search"])
        assert result.exit_code == 1

    def test_search_description_truncated(self, monkeypatch, tmp_path):
        """Long descriptions are truncated in table output."""
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        repo = ProjectRepository(conn)
        repo.create(
            title="Long desc project",
            slug="2026-01-01-long-desc",
            description="A" * 60,  # Longer than 40 char limit
            domain="test",
        )
        conn.close()

        result = runner.invoke(app, ["search", "Long desc"])
        assert result.exit_code == 0
        # Rich may use "…" (ellipsis) or "..." for truncation
        assert "…" in result.output or "..." in result.output


# ---------------------------------------------------------------------------
# export command
# ---------------------------------------------------------------------------


class TestExportCommand:
    def test_export_single(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["export", "2026-01-01-customer-churn-analysis"])
        assert result.exit_code == 0
        # Rich syntax highlighting wraps JSON, just check slug appears
        assert "customer-churn-analysis" in result.output

    def test_export_all(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["export", "--all"])
        assert result.exit_code == 0
        assert "count" in result.output

    def test_export_no_slug_defaults_all(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        result = runner.invoke(app, ["export"])
        assert result.exit_code == 0

    def test_export_not_found(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        _patch_conn(monkeypatch, tmp_path)

        result = runner.invoke(app, ["export", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_export_to_file(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        out_file = str(tmp_path / "export.json")
        result = runner.invoke(
            app,
            ["export", "2026-01-01-customer-churn-analysis", "--output", out_file],
        )
        assert result.exit_code == 0
        assert "Exported to" in result.output

        from pathlib import Path

        content = Path(out_file).read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["slug"] == "2026-01-01-customer-churn-analysis"

    def test_export_compact(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        _seed_projects(db_path)

        out_file = str(tmp_path / "compact.json")
        result = runner.invoke(
            app,
            [
                "export",
                "2026-01-01-customer-churn-analysis",
                "--compact",
                "--output",
                out_file,
            ],
        )
        assert result.exit_code == 0

        from pathlib import Path

        content = Path(out_file).read_text(encoding="utf-8").strip()
        assert "\n" not in content  # compact = no indentation


# ---------------------------------------------------------------------------
# config init command
# ---------------------------------------------------------------------------


class TestConfigInitCommand:
    def test_config_init(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        config_path = tmp_path / "config.json"
        monkeypatch.setattr(
            "data_project_manager.config.loader.CONFIG_PATH", config_path
        )

        result = runner.invoke(app, ["config", "init"])
        assert result.exit_code == 0
        assert "Config initialised" in result.output
        assert config_path.exists()

    def test_config_init_already_exists(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        config_path = tmp_path / "config.json"
        config_path.write_text("{}")
        monkeypatch.setattr(
            "data_project_manager.config.loader.CONFIG_PATH", config_path
        )

        result = runner.invoke(app, ["config", "init"])
        assert result.exit_code == 1

    def test_config_init_force(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        config_path = tmp_path / "config.json"
        config_path.write_text("{}")
        monkeypatch.setattr(
            "data_project_manager.config.loader.CONFIG_PATH", config_path
        )

        result = runner.invoke(app, ["config", "init", "--force"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# new command (non-interactive with all flags)
# ---------------------------------------------------------------------------


class TestNewCommand:
    @staticmethod
    def _config_for(db_path: str, root_dir: str) -> dict:
        return {
            "general": {"db_path": db_path, "default_root": "test"},
            "roots": {"test": {"path": root_dir}},
            "defaults": {"template": "analysis", "git_init": False},
            "preferences": {"folder_language": "en"},
            "templates": {},
        }

    def test_new_with_all_flags(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        root_dir = str(tmp_path / "projects")
        (tmp_path / "projects").mkdir()

        monkeypatch.setattr(
            "data_project_manager.config.loader.load_config",
            lambda _p=None: self._config_for(db_path, root_dir),
        )

        result = runner.invoke(
            app,
            [
                "new",
                "Test Project",
                "--domain",
                "test",
                "--description",
                "A test",
                "--type",
                "minimal",
                "--no-git",
            ],
        )
        assert result.exit_code == 0
        assert "Project created" in result.output

    def test_new_with_explicit_folders(self, monkeypatch, tmp_path):
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        root_dir = str(tmp_path / "projects")
        (tmp_path / "projects").mkdir()

        monkeypatch.setattr(
            "data_project_manager.config.loader.load_config",
            lambda _p=None: self._config_for(db_path, root_dir),
        )

        result = runner.invoke(
            app,
            [
                "new",
                "Folder Test",
                "--domain",
                "test",
                "--description",
                "test",
                "--folder",
                "data",
                "--folder",
                "src",
                "--no-git",
            ],
        )
        assert result.exit_code == 0
        assert "Project created" in result.output

    def test_new_duplicate_name_fails(self, monkeypatch, tmp_path):
        """Creating a project in a folder that already exists should fail."""
        from data_project_manager.cli.app import app

        db_path = _patch_conn(monkeypatch, tmp_path)
        root_dir = str(tmp_path / "projects")
        (tmp_path / "projects").mkdir()

        monkeypatch.setattr(
            "data_project_manager.config.loader.load_config",
            lambda _p=None: self._config_for(db_path, root_dir),
        )

        new_args = [
            "new",
            "Dup Test",
            "--domain",
            "test",
            "--description",
            "test",
            "--type",
            "minimal",
            "--no-git",
        ]
        runner.invoke(app, new_args)
        result = runner.invoke(app, new_args)
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_status_text_known(self):
        from data_project_manager.cli.app import _status_text

        t = _status_text("active")
        assert str(t) == "active"

    def test_status_text_unknown(self):
        from data_project_manager.cli.app import _status_text

        t = _status_text("custom-status")
        assert str(t) == "custom-status"
