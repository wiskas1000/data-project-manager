# CLAUDE.md — Data Project Manager

## Project Overview

A project launcher and metadata database for analytical work. The primary interface is `datapm new` — an interactive command that scaffolds project folders, asks a few questions, and writes structured metadata to a SQLite database. The database and its repository classes also serve as a Python library that other tools (data pipelines, scanners, web dashboards) can import and write to. The core runs on **any Python 3.11+ machine with zero external dependencies**.

## What This Tool Is

- A **launcher**: `datapm new` creates dated project folders with standard subfolders and metadata
- A **schema owner**: the SQLite database holds the canonical data model for projects, people, files, and sensitivity
- A **Python library**: other scripts import `from data_project_manager.db.repositories import ...` to read/write project data
- A **search index**: `datapm search` finds projects across the entire history by metadata
- A **JSON exporter**: `datapm export` dumps structured metadata for LLM context or downstream tools

## What This Tool Is NOT (for now)

- Not a manual data entry system — no need to type `datapm files add` for every file
- Not a project management tool — Trello/DevOps/Jira handles task tracking
- Not a file watcher — auto-scanning is a post-v1.0.0 feature

## Tech Stack

- **Language**: Python ≥ 3.11
- **Package manager**: [uv](https://docs.astral.sh/uv/) (preferred) — pip + venv as fallback
- **Database**: SQLite via stdlib `sqlite3`, Repository Pattern
- **Config**: JSON via stdlib `json` — `~/.datapm/config.json`
- **Project metadata**: JSON via stdlib `json` — `project.json` per project
- **CLI (core)**: stdlib `argparse` — zero-dependency, works everywhere
- **CLI (enhanced)**: [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) — optional
- **Testing**: [pytest](https://pytest.org/) + [pytest-cov](https://pytest-cov.readthedocs.io/) (dev only)
- **Linting**: [ruff](https://docs.astral.sh/ruff/) (dev only)
- **Docs**: [Sphinx](https://www.sphinx-doc.org/) with autodoc (dev only)
- **Hooks**: [pre-commit](https://pre-commit.com/) (dev only)

### Runtime Dependencies

**Core mode**: Python 3.11+ stdlib only — zero external dependencies.

**Enhanced mode** (optional): `typer[all]` for interactive prompts and Rich formatting.

## Running the Tool

```bash
# Development (uv)
uv run datapm new "My Project" --domain healthcare
uv run datapm search "churn"
uv run datapm export my-project

# Fallback (pip)
pip install -e .
python -m data_project_manager new "My Project"

# Absolute minimum (just Python)
python -m data_project_manager new "My Project"
```

## Using as a Library

Other scripts can import the repository classes to read/write project data:

```python
from data_project_manager.db.connection import get_connection
from data_project_manager.db.repositories.data_file import DataFileRepository

conn = get_connection()
repo = DataFileRepository(conn)
repo.create(
    project_id="...",
    file_path="data/raw/customers_2026Q1.csv",
    sensitivity="client_confidential",
    entity_type=["customers"],
    aggregation_level=["row"],
)
```

`get_connection()` reads `~/.datapm/config.json` to find the database path (defaults to `~/.datapm/projects.db`). If the config doesn't exist yet, it falls back to the default location. You can also pass an explicit path: `get_connection(db_path="/path/to/my.db")`.

This is how data pipelines, scanners, and future integrations populate the database — not manual CLI commands.

## Repository Structure

Only create files when needed for the current milestone.

```
data-project-manager/
├── CLAUDE.md
├── pyproject.toml
├── uv.lock
├── .pre-commit-config.yaml
├── .gitignore
├── README.md
├── CHANGELOG.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PLAN.md
│   └── TECH_STACK.md
├── src/
│   └── data_project_manager/
│       ├── __init__.py
│       ├── __main__.py         # two-tier CLI entry point
│       ├── cli/
│       │   └── __init__.py
│       ├── core/               # business logic (stdlib only)
│       │   └── __init__.py
│       ├── db/                 # database layer (stdlib sqlite3)
│       │   ├── __init__.py
│       │   ├── connection.py
│       │   ├── schema.py       # DDL + version-based migrations
│       │   └── repositories/
│       │       └── __init__.py
│       └── config/
│           └── __init__.py
└── tests/
    └── conftest.py
```

## Two-Tier CLI

```python
#!/usr/bin/env python3
# src/data_project_manager/__main__.py
try:
    from data_project_manager.cli.app import app
    app()
except ImportError:
    from data_project_manager.cli.fallback import main
    main()
```

Build argparse first (works everywhere). Add Typer wrapper after. `core/` and `db/` must NEVER import optional dependencies.

## Database Migrations

Version-based system in `db/schema.py`:

```python
SCHEMA_VERSION = 2

MIGRATIONS = {
    1: [
        "CREATE TABLE project (...);",
        "CREATE TABLE project_root (...);",
    ],
    2: [
        "CREATE TABLE person (...);",
        "CREATE TABLE tag (...);",
        "CREATE TABLE data_file (...);",
        # ... remaining 14 tables from ARCHITECTURE.md
    ],
}

def migrate(conn):
    current = get_schema_version(conn)
    for version in range(current + 1, SCHEMA_VERSION + 1):
        for statement in MIGRATIONS[version]:
            conn.execute(statement)
    set_schema_version(conn, SCHEMA_VERSION)
```

All 16 tables are created across migrations as the schema evolves. Migration 1 covers Project and ProjectRoot. Migration 2 adds the remaining 14 tables. Future schema changes add new migration numbers.

## Repository Pattern

`db/repositories/` — one file per entity group:

- `project.py` — Project, ProjectRoot
- `person.py` — Person (SCD2), ProjectPerson
- `tag.py` — Tag, ProjectTag
- `data_file.py` — DataFile, EntityType, AggregationLevel, junction tables
- `deliverable.py` — Deliverable, DeliverableDataFile
- `query.py` — Query
- `question.py` — RequestQuestion
- `changelog.py` — ChangeLog

These are created as needed per milestone. v0.1.0 only needs `project.py`. v0.2.0 adds the rest to expose the full schema as a Python API.

## Branch Naming

`type/short-description` — types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

## Commit Messages

Conventional Commits: `type(scope): description` — imperative mood, ≤ 72 chars, one logical change per commit.

## Pull Requests

Title mirrors branch. Body: **Why** + **What changed**. Small and reviewable.

## Testing

pytest. Write tests before marking complete. Core/DB tests must pass without optional deps.

## Linting

ruff (format + lint), enforced via pre-commit hooks.

## Git Hooks

pre-commit: `ruff check` + `ruff format --check`. pre-push: `uv run pytest`.

## Docstrings

Google style. Required on all public functions and classes once past draft stage.

## Versioning

Semver tags at each milestone: v0.1.0, v0.2.0, v0.3.0, v1.0.0.

## Security

No secrets in code. `.env` + `os.environ`. `.env` in `.gitignore`.

## Design Principles

1. **Zero-dependency core** — `core/` and `db/` use only stdlib
2. **Library first, CLI second** — the repository classes are the primary API; CLI wraps them
3. **Schema up front, commands on demand** — all 16 tables exist from v0.2.0; CLI commands only for launcher, search, export
4. **Argparse first, Typer second** — stdlib CLI works everywhere; Typer adds polish
5. **Repository pattern** — clean Python API over raw SQL, one file per entity group, swappable for ORM later
6. **Cross-platform** — `pathlib.Path` everywhere
7. **SQLite is source of truth** — `project.json` is a one-directional export (DB → JSON), not a sync mechanism. It is created during `datapm new` and refreshed by `datapm export <project>`. The `datapm project update` command does NOT auto-refresh `project.json` — run `datapm export` explicitly when a fresh copy is needed.
