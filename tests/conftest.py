"""Shared test fixtures."""

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(tmp_path: Path) -> sqlite3.Connection:
    """Provide a temporary in-memory SQLite connection."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def tmp_project_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for project scaffolding tests."""
    return tmp_path / "projects"
