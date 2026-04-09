"""Tests for 'datapm project update' and 'datapm info' commands (argparse fallback)."""

import argparse

from helpers import make_project

from data_project_manager.cli.fallback import (
    _handle_info,
    _handle_project_update,
)
from data_project_manager.db.connection import get_connection
from data_project_manager.db.repositories.changelog import ChangeLogRepository
from data_project_manager.db.repositories.project import ProjectRepository
from data_project_manager.db.repositories.tag import ProjectTagRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _update_args(slug: str, **kwargs) -> argparse.Namespace:
    """Build a Namespace as argparse would for 'project update'."""
    return argparse.Namespace(
        slug=slug,
        status=kwargs.get("status"),
        domain=kwargs.get("domain"),
        description=kwargs.get("description"),
        external_url=kwargs.get("external_url"),
        tags=kwargs.get("tags"),
        remove_tags=kwargs.get("remove_tags"),
    )


def _info_args(slug: str) -> argparse.Namespace:
    return argparse.Namespace(slug=slug)


def _patch_conn(monkeypatch, tmp_path):
    """Patch get_connection at the source module so handler local imports see it."""
    db_path = str(tmp_path / "test.db")
    import data_project_manager.db.connection as _conn_mod

    monkeypatch.setattr(
        _conn_mod, "get_connection", lambda _p=None: get_connection(db_path)
    )
    return db_path


# ---------------------------------------------------------------------------
# project update — core field changes
# ---------------------------------------------------------------------------


class TestProjectUpdate:
    def test_update_status(self, tmp_path, monkeypatch) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn)
        conn.close()

        _handle_project_update(_update_args(project.slug, status="done"))

        conn2 = get_connection(db_path)
        updated = ProjectRepository(conn2).get_by_slug(project.slug)
        assert updated.status == "done"
        conn2.close()

    def test_update_domain(self, tmp_path, monkeypatch) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn)
        conn.close()

        _handle_project_update(_update_args(project.slug, domain="healthcare"))

        conn2 = get_connection(db_path)
        updated = ProjectRepository(conn2).get_by_slug(project.slug)
        assert updated.domain == "healthcare"
        conn2.close()

    def test_update_description(self, tmp_path, monkeypatch) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn)
        conn.close()

        _handle_project_update(
            _update_args(project.slug, description="New description")
        )

        conn2 = get_connection(db_path)
        updated = ProjectRepository(conn2).get_by_slug(project.slug)
        assert updated.description == "New description"
        conn2.close()

    def test_update_nothing_prints_message(self, tmp_path, monkeypatch, capsys) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn)
        conn.close()

        _handle_project_update(_update_args(project.slug))
        captured = capsys.readouterr()
        assert "Nothing to update" in captured.out

    def test_update_invalid_status_exits(self, tmp_path, monkeypatch) -> None:
        import pytest

        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn)
        conn.close()

        with pytest.raises(SystemExit):
            _handle_project_update(_update_args(project.slug, status="invalid"))

    def test_update_missing_slug_exits(self, tmp_path, monkeypatch) -> None:
        import pytest

        db_path = _patch_conn(monkeypatch, tmp_path)
        # DB exists but is empty (no projects)
        get_connection(db_path).close()

        with pytest.raises(SystemExit):
            _handle_project_update(_update_args("no-such-slug", status="done"))

    def test_add_tag(self, tmp_path, monkeypatch) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn)
        conn.close()

        _handle_project_update(_update_args(project.slug, tags=["ml", "churn"]))

        conn2 = get_connection(db_path)
        tags = ProjectTagRepository(conn2).list_for_project(project.id)
        assert {t.name for t in tags} == {"ml", "churn"}
        conn2.close()

    def test_remove_tag(self, tmp_path, monkeypatch) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn)
        conn.close()

        _handle_project_update(_update_args(project.slug, tags=["ml"]))
        _handle_project_update(_update_args(project.slug, remove_tags=["ml"]))

        conn2 = get_connection(db_path)
        tags = ProjectTagRepository(conn2).list_for_project(project.id)
        assert tags == []
        conn2.close()

    def test_update_writes_changelog(self, tmp_path, monkeypatch) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn)
        conn.close()

        _handle_project_update(_update_args(project.slug, status="done"))

        conn2 = get_connection(db_path)
        log = ChangeLogRepository(conn2).list_for_entity("project", project.id)
        assert any(e.field_name == "status" for e in log)
        conn2.close()

    def test_update_prints_summary(self, tmp_path, monkeypatch, capsys) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn)
        conn.close()

        _handle_project_update(_update_args(project.slug, status="paused"))
        out = capsys.readouterr().out
        assert "Updated" in out
        assert "status" in out


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


class TestInfo:
    def test_info_prints_title_and_slug(self, tmp_path, monkeypatch, capsys) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn, "My Analysis")
        conn.close()

        _handle_info(_info_args(project.slug))
        out = capsys.readouterr().out
        assert "My Analysis" in out
        assert project.slug in out

    def test_info_shows_status(self, tmp_path, monkeypatch, capsys) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn)
        conn.close()

        _handle_info(_info_args(project.slug))
        assert "active" in capsys.readouterr().out

    def test_info_shows_tags(self, tmp_path, monkeypatch, capsys) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn)
        conn.close()

        _handle_project_update(_update_args(project.slug, tags=["ml"]))
        _handle_info(_info_args(project.slug))
        assert "ml" in capsys.readouterr().out

    def test_info_shows_changelog(self, tmp_path, monkeypatch, capsys) -> None:
        db_path = _patch_conn(monkeypatch, tmp_path)
        conn = get_connection(db_path)
        project = make_project(conn)
        conn.close()

        _handle_project_update(_update_args(project.slug, status="done"))
        _handle_info(_info_args(project.slug))
        out = capsys.readouterr().out
        assert "status" in out

    def test_info_missing_slug_exits(self, tmp_path, monkeypatch) -> None:
        import pytest

        db_path = _patch_conn(monkeypatch, tmp_path)
        get_connection(db_path).close()

        with pytest.raises(SystemExit):
            _handle_info(_info_args("no-such-slug"))
