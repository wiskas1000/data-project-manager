"""Shared test fixtures."""

import sqlite3

import pytest
from helpers import fresh_conn


@pytest.fixture()
def db_conn() -> sqlite3.Connection:
    """Return a migrated in-memory SQLite connection."""
    return fresh_conn()
