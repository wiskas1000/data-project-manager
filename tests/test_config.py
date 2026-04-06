"""Tests for config/loader.py and config/defaults.py."""

import json
from pathlib import Path

import pytest

from data_project_manager.config.defaults import DB_PATH, DEFAULT_CONFIG
from data_project_manager.config.loader import (
    get_db_path,
    get_default_root,
    get_root_path,
    init_config,
    load_config,
    save_config,
)

# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


def test_load_config_missing_file_returns_defaults(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "nonexistent.json")
    assert cfg["general"]["default_root"] == DEFAULT_CONFIG["general"]["default_root"]
    assert "roots" in cfg
    assert "defaults" in cfg


def test_load_config_reads_existing_file(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    data = json.dumps({"general": {"default_root": "personal"}})
    p.write_text(data, encoding="utf-8")
    cfg = load_config(p)
    assert cfg["general"]["default_root"] == "personal"


def test_load_config_merges_missing_keys(tmp_path: Path) -> None:
    """On-disk config missing some keys should be filled from defaults."""
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"general": {"default_root": "x"}}), encoding="utf-8")
    cfg = load_config(p)
    # "defaults" section comes from DEFAULT_CONFIG
    assert "template" in cfg["defaults"]


def test_load_config_override_wins(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    p.write_text(
        json.dumps({"defaults": {"template": "full", "git_init": False}}),
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg["defaults"]["template"] == "full"
    assert cfg["defaults"]["git_init"] is False


# ---------------------------------------------------------------------------
# save_config / init_config
# ---------------------------------------------------------------------------


def test_save_config_creates_file(tmp_path: Path) -> None:
    p = tmp_path / "sub" / "config.json"
    save_config({"general": {"default_root": "work"}}, p)
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["general"]["default_root"] == "work"


def test_init_config_creates_default_file(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    result = init_config(p)
    assert result == p
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "roots" in data


def test_init_config_raises_if_exists(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):
        init_config(p)


def test_init_config_force_overwrites(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    p.write_text("{}", encoding="utf-8")
    init_config(p, force=True)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "roots" in data


# ---------------------------------------------------------------------------
# get_db_path
# ---------------------------------------------------------------------------


def test_get_db_path_default(tmp_path: Path) -> None:
    assert get_db_path(tmp_path / "missing.json") == DB_PATH


def test_get_db_path_from_config(tmp_path: Path) -> None:
    custom_db = tmp_path / "mydb.db"
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"general": {"db_path": str(custom_db)}}), encoding="utf-8")
    assert get_db_path(p) == custom_db


# ---------------------------------------------------------------------------
# get_default_root / get_root_path
# ---------------------------------------------------------------------------


def test_get_default_root(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    data = json.dumps({"general": {"default_root": "personal"}})
    p.write_text(data, encoding="utf-8")
    assert get_default_root(p) == "personal"


def test_get_default_root_missing_file(tmp_path: Path) -> None:
    result = get_default_root(tmp_path / "missing.json")
    assert result == DEFAULT_CONFIG["general"]["default_root"]


def test_get_root_path_known_root(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    p.write_text(
        json.dumps({"roots": {"work": {"path": "/projects/work"}}}), encoding="utf-8"
    )
    assert get_root_path("work", p) == Path("/projects/work")


def test_get_root_path_unknown_root(tmp_path: Path) -> None:
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"roots": {}}), encoding="utf-8")
    assert get_root_path("nonexistent", p) is None
