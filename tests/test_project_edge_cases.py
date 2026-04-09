"""Edge case tests for core/project.py — git init failures, root resolution."""

import subprocess
from unittest.mock import patch

import pytest

from data_project_manager.core.project import (
    create_project,
    git_init_project,
)


class TestGitInitProject:
    def test_missing_dir(self, tmp_path):
        """git_init_project returns False when src/ doesn't exist."""
        result = git_init_project(tmp_path / "nonexistent")
        assert result is False

    def test_git_not_on_path(self, tmp_path):
        """git_init_project returns False when git is not installed."""
        src = tmp_path / "src"
        src.mkdir()

        with patch("data_project_manager.core.project.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")
            result = git_init_project(src)
        assert result is False

    def test_git_init_fails(self, tmp_path):
        """git_init_project returns False when git init returns non-zero."""
        src = tmp_path / "src"
        src.mkdir()

        with patch("data_project_manager.core.project.subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=["git", "init"], returncode=1, stdout="", stderr="error"
            )
            result = git_init_project(src)
        assert result is False


class TestCreateProjectRootResolution:
    def test_create_with_named_root(self, tmp_path):
        """Create project using a named root from config."""
        db_path = str(tmp_path / "test.db")
        root_dir = tmp_path / "projects"
        root_dir.mkdir()
        config_path = tmp_path / "config.json"

        import json

        config_path.write_text(
            json.dumps(
                {
                    "general": {
                        "db_path": db_path,
                        "default_root": "work",
                    },
                    "roots": {
                        "work": {"path": str(root_dir)},
                    },
                    "defaults": {"template": "minimal"},
                    "preferences": {"folder_language": "en"},
                    "templates": {},
                }
            )
        )

        result = create_project(
            "Root Test",
            template_used="minimal",
            do_git_init=False,
            db_path=db_path,
            config_path=config_path,
        )
        assert root_dir.name in result["project_path"]

    def test_create_with_root_not_in_db(self, tmp_path):
        """Root exists in config but not yet in DB — should be auto-created."""
        db_path = str(tmp_path / "test.db")
        root_dir = tmp_path / "new_root"
        root_dir.mkdir()
        config_path = tmp_path / "config.json"

        import json

        config_path.write_text(
            json.dumps(
                {
                    "general": {
                        "db_path": db_path,
                        "default_root": "fresh",
                    },
                    "roots": {
                        "fresh": {"path": str(root_dir)},
                    },
                    "defaults": {"template": "minimal"},
                    "preferences": {"folder_language": "en"},
                    "templates": {},
                }
            )
        )

        result = create_project(
            "Fresh Root",
            template_used="minimal",
            do_git_init=False,
            db_path=db_path,
            config_path=config_path,
        )
        assert str(root_dir) in result["project_path"]

    def test_create_git_init_failure_clears_flag(self, tmp_path):
        """When git init fails, has_git_repo is set to False."""
        db_path = str(tmp_path / "test.db")

        with patch("data_project_manager.core.project.git_init_project") as mock:
            mock.return_value = False
            result = create_project(
                "Git Fail",
                template_used="analysis",
                do_git_init=True,
                root_path_override=tmp_path,
                db_path=db_path,
                language="en",
            )

        assert result["has_git_repo"] is False

    def test_create_project_folder_exists(self, tmp_path):
        """Error when project folder already exists."""
        db_path = str(tmp_path / "test.db")

        # Create the project once
        create_project(
            "Exists Test",
            template_used="minimal",
            do_git_init=False,
            root_path_override=tmp_path,
            db_path=db_path,
        )

        # Second call should fail because folder exists
        with pytest.raises(FileExistsError):
            create_project(
                "Exists Test",
                template_used="minimal",
                do_git_init=False,
                root_path_override=tmp_path,
                db_path=db_path,
            )
