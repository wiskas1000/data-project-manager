# Data Project Manager

A project launcher and metadata database for analytical work.

`datapm new` creates a dated folder, asks a few questions, and writes
structured metadata to a local SQLite database. The database can also be
imported directly by data pipelines, scanners, and dashboards via the
Python repository API.

## Features (v0.1.0)

- **`datapm new`** — interactive or one-liner project creation; scaffolds
  dated folders with standard Dutch subfolders, writes `project.json`,
  and optionally runs `git init`
- **`datapm list`** — tabular view of all projects with status and domain
- **`datapm config init`** — creates `~/.datapm/config.json` with sensible
  defaults
- **Zero runtime dependencies** — core and DB layers use stdlib only
- **Enhanced mode** — install `typer` for Rich-formatted, colour-coded
  terminal output

## Requirements

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

```bash
# Development (uv)
git clone https://github.com/wiskas1000/data-project-manager
cd data-project-manager
uv sync

# With enhanced (Rich) output
uv sync --extra enhanced

# pip
pip install -e .
pip install -e ".[enhanced]"   # Rich output
```

## Quick start

```bash
# 1 — Initialise config (creates ~/.datapm/config.json)
datapm config init

# 2 — Create a project interactively
datapm new

# 2b — One-liner
datapm new "Churn analysis" --domain marketing --folder data --folder notebooks --git

# 3 — List all projects
datapm list
datapm list --status active --domain marketing

# Zero-dependency fallback (no Typer needed)
python -m data_project_manager new "My Project"
```

## Project folder layout

```
2026-04-07_Churn-Analysis/
├── archief/
├── communicatie/
├── documenten/
├── project.json          ← metadata snapshot (DB is source of truth)
└── .gitignore            ← present when --git is used
```

Optional folder groups added via `--folder`:

| Key | Creates |
|-----|---------|
| `data` | `data/raw/`, `data/processed/`, `data/metadata/` |
| `src` | `src/queries/` |
| `literatuur` | `literatuur/` |
| `resultaten` | `resultaten/export/`, `resultaten/figuren/` |
| `notebooks` | `notebooks/` |

## Using as a library

Other scripts can import the repository classes to read/write project data
without going through the CLI:

```python
from data_project_manager.db.connection import get_connection
from data_project_manager.db.repositories.project import ProjectRepository

conn = get_connection()           # reads ~/.datapm/config.json
repo = ProjectRepository(conn)
projects = repo.list(status="active", domain="healthcare")
```

`get_connection()` accepts an explicit `db_path` argument — useful in
scripts and tests:

```python
conn = get_connection("/path/to/my.db")
```

## Configuration

`~/.datapm/config.json` (created by `datapm config init`):

```json
{
  "general": { "default_root": "work" },
  "roots": {
    "work": { "path": "/home/user/projects/work" }
  },
  "defaults": { "template": "minimal", "git_init": true, "sensitivity": "internal" },
  "preferences": { "folder_language": "nl" }
}
```

Add a custom `db_path` under `general` to store the database somewhere
other than `~/.datapm/projects.db`.

## Development

```bash
uv sync --extra enhanced
uv run pre-commit install
uv run pre-commit install --hook-type pre-push

uv run pytest              # tests
uv run ruff check .        # lint
uv run ruff format .       # format
uv run datapm --help       # Typer CLI
uv run python -m data_project_manager --help  # argparse fallback
```

A **Makefile** wraps these for convenience:

```bash
make test       # run tests
make check      # lint + format check + tests
make cov        # tests with coverage report
make format     # auto-format
make docs       # build Sphinx docs
make clean      # remove caches and build artifacts
make help       # list all targets
```

## Roadmap

See [docs/PLAN.md](docs/PLAN.md) for the full milestone plan.

| Milestone | Tag | Focus |
|-----------|-----|-------|
| Launcher | **v0.1.0** | `datapm new`, config, DB foundation ✓ |
| Full Schema & Library API | v0.2.0 | All 16 tables, repository classes, Python API |
| Search & Export | v0.3.0 | FTS5 search, JSON export |
| Docs & v1 Release | v1.0.0 | Coverage, documentation, stability |

## License

MIT
