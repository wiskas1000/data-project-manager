"""Tests for config/loader.py — covering edge cases and remaining gaps."""

import json
from pathlib import Path

from data_project_manager.config.loader import (
    get_config_path,
    get_custom_templates,
    get_default_template,
    get_folder_language,
    get_git_init_default,
)


class TestGetConfigPath:
    def test_returns_path(self):
        path = get_config_path()
        assert isinstance(path, Path)
        assert path.name == "config.json"


class TestGetDefaultTemplate:
    def test_default_when_no_config(self, tmp_path):
        path = tmp_path / "missing.json"
        result = get_default_template(path)
        assert result == "analysis"

    def test_custom_template(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"defaults": {"template": "full"}}))
        result = get_default_template(path)
        assert result == "full"


class TestGetFolderLanguage:
    def test_default_when_no_config(self, tmp_path):
        path = tmp_path / "missing.json"
        result = get_folder_language(path)
        assert result == "nl"

    def test_custom_language(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"preferences": {"folder_language": "en"}}))
        result = get_folder_language(path)
        assert result == "en"


class TestGetCustomTemplates:
    def test_default_empty(self, tmp_path):
        path = tmp_path / "missing.json"
        result = get_custom_templates(path)
        assert result == {}

    def test_with_templates(self, tmp_path):
        path = tmp_path / "config.json"
        data = {
            "templates": {
                "custom1": {"description": "My template", "folders": ["data"]}
            }
        }
        path.write_text(json.dumps(data))
        result = get_custom_templates(path)
        assert "custom1" in result


class TestGetGitInitDefault:
    def test_default_from_skeleton(self, tmp_path):
        """When no config file exists, the DEFAULT_CONFIG skeleton provides True."""
        path = tmp_path / "missing.json"
        result = get_git_init_default(path)
        assert result is True

    def test_explicitly_none(self, tmp_path):
        """When config explicitly nulls git_init, returns None."""
        path = tmp_path / "config.json"
        # Must explicitly set to null; empty dict gets merged with defaults
        path.write_text(json.dumps({"defaults": {"git_init": None}}))
        result = get_git_init_default(path)
        assert result is None

    def test_set_true(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"defaults": {"git_init": True}}))
        result = get_git_init_default(path)
        assert result is True

    def test_set_false(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"defaults": {"git_init": False}}))
        result = get_git_init_default(path)
        assert result is False
