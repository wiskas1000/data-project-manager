"""Person dataclass (SCD Type 2)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Person:
    """A person tracked with SCD Type 2 versioning."""

    id: str
    first_name: str
    last_name: str
    email: str | None
    function_title: str | None
    department: str | None
    valid_from: str
    valid_to: str | None
    is_current: bool
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> Person:
        """Construct from a :class:`sqlite3.Row`."""
        d = dict(row)
        d["is_current"] = bool(d["is_current"])
        return cls(**d)


@dataclass(frozen=True)
class PersonWithRole:
    """A person joined with their role on a project.

    Returned by :meth:`ProjectPersonRepository.list_for_project`.
    """

    role: str
    id: str
    first_name: str
    last_name: str
    email: str | None
    function_title: str | None
    department: str | None
    valid_from: str
    valid_to: str | None
    is_current: bool
    created_at: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> PersonWithRole:
        """Construct from a joined :class:`sqlite3.Row` (role + person.*)."""
        d = dict(row)
        d["is_current"] = bool(d["is_current"])
        return cls(**d)


@dataclass(frozen=True)
class ProjectPersonLink:
    """A project-role link for a person.

    Returned by :meth:`ProjectPersonRepository.list_for_person`.
    """

    project_id: str
    role: str
