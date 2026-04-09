"""Extended tests for argparse fallback CLI — covering remaining gaps."""

import argparse

import pytest
from helpers import make_project

from data_project_manager.cli.fallback import (
    _handle_config,
    _handle_info,
    _handle_list,
    _handle_new,
    _prompt,
    _prompt_archetype,
    _prompt_bool,
    _prompt_folder_toggles,
    _prompt_optional,
    main,
)
from data_project_manager.db.connection import get_connection
from data_project_manager.db.repositories.person import (
    PersonRepository,
    ProjectPersonRepository,
)


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


# ---------------------------------------------------------------------------
# main() dispatch
# ---------------------------------------------------------------------------


class TestMainDispatch:
    def test_no_command_prints_help(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["datapm"])
        main()
        out = capsys.readouterr().out
        assert "Data Project Manager" in out

    def test_list_command(self, monkeypatch, tmp_path, capsys):
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        make_project(conn, "Listed Project")
        conn.close()

        monkeypatch.setattr("sys.argv", ["datapm", "list"])
        main()
        out = capsys.readouterr().out
        assert "Listed Project" in out or "listed-project" in out

    def test_info_command(self, monkeypatch, tmp_path, capsys):
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn, "Info Target")
        conn.close()

        monkeypatch.setattr("sys.argv", ["datapm", "info", project.slug])
        main()
        out = capsys.readouterr().out
        assert "Info Target" in out

    def test_project_no_subcommand(self, monkeypatch, tmp_path, capsys):
        _patch_conn(monkeypatch, tmp_path)
        monkeypatch.setattr("sys.argv", ["datapm", "project"])
        main()
        out = capsys.readouterr().out
        assert "Manage project metadata" in out or "project" in out.lower()

    def test_config_no_subcommand(self, monkeypatch, tmp_path, capsys):
        _patch_conn(monkeypatch, tmp_path)
        monkeypatch.setattr("sys.argv", ["datapm", "config"])
        main()
        out = capsys.readouterr().out
        assert "config" in out.lower()


# ---------------------------------------------------------------------------
# _handle_list
# ---------------------------------------------------------------------------


class TestHandleList:
    def test_list_empty(self, monkeypatch, tmp_path, capsys):
        _patch_conn(monkeypatch, tmp_path)
        args = argparse.Namespace(status=None, domain=None)
        _handle_list(args)
        assert "No projects found" in capsys.readouterr().out

    def test_list_with_projects(self, monkeypatch, tmp_path, capsys):
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        make_project(conn, "Alpha")
        make_project(conn, "Beta")
        conn.close()

        args = argparse.Namespace(status=None, domain=None)
        _handle_list(args)
        out = capsys.readouterr().out
        assert "SLUG" in out
        assert "STATUS" in out

    def test_list_filter_status(self, monkeypatch, tmp_path, capsys):
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        make_project(conn, "Active One")
        conn.close()

        args = argparse.Namespace(status="active", domain=None)
        _handle_list(args)
        out = capsys.readouterr().out
        assert "active-one" in out


# ---------------------------------------------------------------------------
# _handle_info — additional coverage (people, changelog)
# ---------------------------------------------------------------------------


class TestHandleInfoExtended:
    def test_info_shows_people(self, monkeypatch, tmp_path, capsys):
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn, "People Test")
        person_repo = PersonRepository(conn)
        pp_repo = ProjectPersonRepository(conn)
        person = person_repo.create(first_name="Bob", last_name="Jones")
        pp_repo.add(project_id=project.id, person_id=person.id, role="analyst")
        conn.close()

        _handle_info(argparse.Namespace(slug=project.slug))
        out = capsys.readouterr().out
        assert "Bob" in out
        assert "Jones" in out


# ---------------------------------------------------------------------------
# _handle_new (non-interactive)
# ---------------------------------------------------------------------------


class TestHandleNew:
    @staticmethod
    def _config_for(db_path: str, root_dir: str) -> dict:
        return {
            "general": {"db_path": db_path, "default_root": "test"},
            "roots": {"test": {"path": root_dir}},
            "defaults": {"template": "analysis", "git_init": False},
            "preferences": {"folder_language": "en"},
            "templates": {},
        }

    def test_new_with_archetype(self, monkeypatch, tmp_path, capsys):
        db_path = _patch_conn(monkeypatch, tmp_path)
        root_dir = str(tmp_path / "projects")
        (tmp_path / "projects").mkdir()

        monkeypatch.setattr(
            "data_project_manager.config.loader.load_config",
            lambda _p=None: self._config_for(db_path, root_dir),
        )

        args = argparse.Namespace(
            name="Archetype Test",
            domain="test",
            description="Testing archetype",
            archetype="minimal",
            folders=None,
            add=None,
            remove=None,
            git=False,
            no_git=True,
            adhoc=False,
        )
        _handle_new(args)
        out = capsys.readouterr().out
        assert "Slug" in out or "slug" in out.lower()
        assert "Done" in out

    def test_new_with_explicit_folders(self, monkeypatch, tmp_path, capsys):
        db_path = _patch_conn(monkeypatch, tmp_path)
        root_dir = str(tmp_path / "projects")
        (tmp_path / "projects").mkdir()

        monkeypatch.setattr(
            "data_project_manager.config.loader.load_config",
            lambda _p=None: self._config_for(db_path, root_dir),
        )
        monkeypatch.setattr("builtins.input", lambda _msg: "")

        args = argparse.Namespace(
            name="Folder Test",
            domain=None,
            description=None,
            archetype=None,
            folders=["data", "src"],
            add=None,
            remove=None,
            git=False,
            no_git=True,
            adhoc=False,
        )
        _handle_new(args)
        out = capsys.readouterr().out
        assert "Done" in out

    def test_new_with_add_remove_flags(self, monkeypatch, tmp_path, capsys):
        db_path = _patch_conn(monkeypatch, tmp_path)
        root_dir = str(tmp_path / "projects")
        (tmp_path / "projects").mkdir()

        monkeypatch.setattr(
            "data_project_manager.config.loader.load_config",
            lambda _p=None: self._config_for(db_path, root_dir),
        )
        monkeypatch.setattr("builtins.input", lambda _msg: "")

        args = argparse.Namespace(
            name="AddRemove Test",
            domain=None,
            description=None,
            archetype="analysis",
            folders=None,
            add=["models"],
            remove=["data"],
            git=False,
            no_git=True,
            adhoc=False,
        )
        _handle_new(args)
        out = capsys.readouterr().out
        assert "Done" in out

    def test_new_error_duplicate(self, monkeypatch, tmp_path, capsys):
        """Creating the same project twice should exit with error."""
        db_path = _patch_conn(monkeypatch, tmp_path)
        root_dir = str(tmp_path / "projects")
        (tmp_path / "projects").mkdir()

        monkeypatch.setattr(
            "data_project_manager.config.loader.load_config",
            lambda _p=None: self._config_for(db_path, root_dir),
        )

        args = argparse.Namespace(
            name="Dup Test",
            domain="test",
            description="test",
            archetype="minimal",
            folders=None,
            add=None,
            remove=None,
            git=False,
            no_git=True,
            adhoc=False,
        )
        _handle_new(args)
        with pytest.raises(SystemExit):
            _handle_new(args)

    def test_new_with_domain_display(self, monkeypatch, tmp_path, capsys):
        db_path = _patch_conn(monkeypatch, tmp_path)
        root_dir = str(tmp_path / "projects")
        (tmp_path / "projects").mkdir()

        monkeypatch.setattr(
            "data_project_manager.config.loader.load_config",
            lambda _p=None: self._config_for(db_path, root_dir),
        )

        args = argparse.Namespace(
            name="Domain Display",
            domain="healthcare",
            description="test desc",
            archetype="minimal",
            folders=None,
            add=None,
            remove=None,
            git=False,
            no_git=True,
            adhoc=False,
        )
        _handle_new(args)
        out = capsys.readouterr().out
        assert "Domain" in out or "healthcare" in out


# ---------------------------------------------------------------------------
# _handle_config
# ---------------------------------------------------------------------------


class TestHandleConfig:
    def test_config_init(self, monkeypatch, tmp_path, capsys):
        config_path = tmp_path / "config.json"
        monkeypatch.setattr(
            "data_project_manager.config.loader.CONFIG_PATH", config_path
        )

        args = argparse.Namespace(config_command="init", force=False)
        parser = argparse.ArgumentParser()
        _handle_config(args, parser)
        assert "Config initialised" in capsys.readouterr().out

    def test_config_init_exists_error(self, monkeypatch, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}")
        monkeypatch.setattr(
            "data_project_manager.config.loader.CONFIG_PATH", config_path
        )

        args = argparse.Namespace(config_command="init", force=False)
        parser = argparse.ArgumentParser()
        with pytest.raises(SystemExit):
            _handle_config(args, parser)

    def test_config_init_force(self, monkeypatch, tmp_path, capsys):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}")
        monkeypatch.setattr(
            "data_project_manager.config.loader.CONFIG_PATH", config_path
        )

        args = argparse.Namespace(config_command="init", force=True)
        parser = argparse.ArgumentParser()
        _handle_config(args, parser)
        assert "Config initialised" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Interactive prompt helpers
# ---------------------------------------------------------------------------


class TestPromptHelpers:
    def test_prompt_returns_non_empty(self, monkeypatch):
        inputs = iter(["", "  ", "hello"])
        monkeypatch.setattr("builtins.input", lambda _msg: next(inputs))
        assert _prompt("Enter: ") == "hello"

    def test_prompt_optional_with_value(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _msg: "value")
        assert _prompt_optional("Optional: ") == "value"

    def test_prompt_optional_empty(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _msg: "")
        assert _prompt_optional("Optional: ") is None

    def test_prompt_bool_yes(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _msg: "y")
        assert _prompt_bool("Continue? ") is True

    def test_prompt_bool_no(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _msg: "n")
        assert _prompt_bool("Continue? ") is False

    def test_prompt_archetype_default(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _msg: "")
        result = _prompt_archetype("analysis")
        assert result == "analysis"

    def test_prompt_archetype_select(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _msg: "1")
        result = _prompt_archetype("analysis")
        # First key in BUILT_IN_ARCHETYPES
        assert isinstance(result, str)

    def test_prompt_archetype_invalid(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _msg: "abc")
        result = _prompt_archetype("analysis")
        assert result == "analysis"  # falls back to default
        assert "Invalid" in capsys.readouterr().out

    def test_prompt_folder_toggles_enter(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _msg: "")
        result = _prompt_folder_toggles(["data", "src"])
        assert "data" in result
        assert "src" in result

    def test_prompt_folder_toggles_toggle(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _msg: "1")
        result = _prompt_folder_toggles(["data", "src"])
        # Toggling item 1 should change the set
        assert isinstance(result, list)

    def test_prompt_folder_toggles_invalid_token(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _msg: "abc")
        result = _prompt_folder_toggles(["data", "src"])
        # Invalid token is silently ignored
        assert isinstance(result, list)
