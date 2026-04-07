# Recommended Tech Stack

## Design Philosophy

**Zero-dependency core.** Runs on any Python 3.11+ machine without installs.

**Library first.** The repository classes are the primary API. CLI, pipelines, scanners, and web dashboards all use the same Python interface.

**Schema up front, commands on demand.** All 16 database tables exist from v0.2.0. CLI commands only cover launcher, search, and export. Everything else writes to the DB via Python imports.

## Core (stdlib only)

| Component | Choice | Why |
|-----------|--------|-----|
| Database | `sqlite3` | Stdlib, zero-config, single file, FTS5. Handles hundreds of projects easily. Every language can read SQLite. |
| DB access | Repository Pattern | Clean Python API per entity group. Pipelines call `repo.create(...)`. Swappable for ORM later. |
| Migrations | Version-based `schema.py` | Numbered migration dict, `_schema_version` table. Simple, explicit. |
| Config | `json` | Stdlib. Read + write. No extra dependency for TOML writing. |
| Metadata | `json` | Stdlib. AI/LLM-native. `jq` and `fzf` compatible. |
| CLI (core) | `argparse` | Stdlib. Always available. |
| Paths | `pathlib` | Stdlib. Cross-platform. |
| IDs | `uuid` | Stdlib. `uuid4()` primary keys. |
| Models | `dataclasses` | Stdlib. Domain objects. |

## Enhanced CLI (optional)

| Component | Choice | Why |
|-----------|--------|-----|
| CLI | [Typer](https://typer.tiangolo.com/) | Auto-help from type hints, interactive prompts. Thin wrapper over same core functions. |
| Output | [Rich](https://rich.readthedocs.io/) | Tables, trees, syntax highlighting. Bundled with `typer[all]`. |

## Development only

| Component | Choice | Why |
|-----------|--------|-----|
| Package manager | [uv](https://docs.astral.sh/uv/) | Fast, lockfile. pip + venv as fallback. |
| Tests | [pytest](https://pytest.org/) + [pytest-cov](https://pytest-cov.readthedocs.io/) | Core/DB tests must pass without optional deps. |
| Lint/format | [ruff](https://docs.astral.sh/ruff/) | Replaces flake8 + isort + black in one tool. |
| Hooks | [pre-commit](https://pre-commit.com/) | Ruff on commit, pytest on push. |
| Docs | [Sphinx](https://www.sphinx-doc.org/) | Autodoc from Google-style docstrings. Especially important for documenting the library API. |

## Why not…

| Alternative | Why not |
|-------------|---------|
| SQLAlchemy | 30MB, learning curve. Repository over sqlite3 gives same clean API. Add later if needed. |
| Alembic | Tied to SQLAlchemy. Version-based migration dict is simpler. |
| YAML | External dep. JSON is stdlib + more LLM-friendly. |
| PostgreSQL | Needs a server. SQLite is portable and sufficient for solo use. |
| Click | If adding a dep, Typer gives more. If zero deps, argparse is stdlib. |
| Cookiecutter | Unreliable in practice. Built-in JSON templates are simpler. |

## pyproject.toml structure

```toml
[project]
name = "data_project_manager"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
enhanced = ["typer"]

[project.scripts]
datapm = "data_project_manager.cli.app:app"

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
```
