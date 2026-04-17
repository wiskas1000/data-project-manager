# Data Project Manager

A project launcher and metadata database for analytical work.

`datapm new` creates a dated folder, asks a few questions, and writes
structured metadata to a local SQLite database. The database can also be
imported directly by data pipelines, scanners, and dashboards via the
Python repository API.

## Features

- **`datapm new`** — interactive or one-liner project creation; scaffolds
  dated folders with archetype-based subfolders, writes `project.json`,
  and optionally runs `git init`
- **`datapm list`** — tabular view of all projects with status and domain
- **`datapm info`** — full metadata for a single project including tags,
  people, and changelog
- **`datapm search`** — FTS5-powered full-text search with structured
  filters (domain, status, tags, date range)
- **`datapm export`** — structured JSON export for LLM context or
  downstream tools
- **`datapm project update`** — update status, domain, tags with
  automatic changelog
- **`datapm config init`** — creates `~/.datapm/config.json` with
  sensible defaults
- **Zero runtime dependencies** — core and DB layers use stdlib only
- **Enhanced mode** — install `typer` for Rich-formatted, colour-coded
  terminal output
- **Python library** — import repository classes directly from data
  pipelines and scripts

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

# 2b — One-liner with archetype
datapm new "Churn Analysis" --domain marketing --type analysis --no-git

# 3 — List and search
datapm list --status active
datapm search "churn" --domain marketing

# 4 — View details and export
datapm info 2026-04-09-churn-analysis
datapm export 2026-04-09-churn-analysis

# 5 — Update metadata
datapm project update 2026-04-09-churn-analysis --status done --tag ml

# Zero-dependency fallback (no Typer needed)
python -m data_project_manager new "My Project"
```

## Project folder layout

```
2026-04-09_Churn-Analysis/
├── communicatie/
├── documenten/
├── data/
│   ├── raw/
│   ├── processed/
│   └── metadata/
├── src/
│   └── queries/
├── project.json          ← metadata snapshot (DB is source of truth)
└── src/.git/             ← present when --git is used
```

Folder structure is controlled by **archetypes** (`--type`):

| Archetype | Folders |
|-----------|---------|
| `minimal` | base only |
| `analysis` | data, src |
| `modeling` | data, src, models |
| `reporting` | data, src, resultaten |
| `research` | data, src, literatuur |
| `full` | everything |

See [docs/usage/templates.rst](docs/usage/templates.rst) for custom
templates and folder language configuration.

## Using as a library

Other scripts can import the repository classes to read/write project
data without going through the CLI:

```python
from data_project_manager.db.connection import get_connection
from data_project_manager.db.repositories.project import ProjectRepository

conn = get_connection()           # reads ~/.datapm/config.json
repo = ProjectRepository(conn)
projects = repo.list(status="active", domain="healthcare")
for p in projects:
    print(p.slug, p.title, p.status)
```

All repositories return **frozen dataclasses** with typed attributes
(`project.id`, `project.slug`).

See [docs/usage/library.rst](docs/usage/library.rst) for a full
pipeline example covering files, people, tags, and deliverables.

## Configuration

`~/.datapm/config.json` (created by `datapm config init`):

```json
{
  "general": { "default_root": "work" },
  "roots": {
    "work": { "path": "/home/user/projects/work" }
  },
  "defaults": { "template": "analysis", "git_init": true, "sensitivity": "internal" },
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

## Documentation

Full Sphinx documentation with API reference:

```bash
make docs       # builds to docs/_build/html/
```

- [Quickstart](docs/usage/quickstart.rst)
- [CLI Reference](docs/usage/cli.rst)
- [Library API Guide](docs/usage/library.rst)
- [Templates & Folders](docs/usage/templates.rst)
- [FAQ](docs/usage/faq.rst)
- [Architecture](docs/ARCHITECTURE.md)
- [Project Plan](docs/PLAN.md)

## Roadmap

See [docs/PLAN.md](docs/PLAN.md) for the full milestone plan.

| Milestone | Tag | Focus |
|-----------|-----|-------|
| Launcher | v0.1.0 | `datapm new`, config, DB foundation |
| Full Schema & Library API | v0.2.0 | All 16 tables, repository classes, Python API |
| Typed Data Model | v0.2.1 | Frozen dataclasses for all entities |
| Search & Export | v0.3.0 | FTS5 search, JSON export |
| Docs & v1 Release | **v1.0.0** | Coverage, documentation, stability |
| Folder Archetypes & CLI Polish | v1.1.0 | Archetype picker, arrow-key toggles, `--type`/`--folder`/`--add`/`--remove` flags |
| Privacy & UI Fixes | v1.1.1 | `--redact` flag, folder toggle dependency fix, display order fix |
| Maintenance | v1.1.2 | Remove unused `row_to_dict()` helper; doc and test top-ups |
| Metadata Search | v1.2.0 | `search_project_metadata()` (tags, people, entity types, agg levels, questions, deliverables); new `entity_types` / `aggregation_levels` / `requestor` filter kwargs on `search_projects()` |

## Privacy

The SQLite database (`~/.datapm/projects.db`) may contain personal data
such as names and email addresses (in the `person` table). **Do not share
the database file** without first reviewing its contents.

When sharing exported JSON, use `--redact` to strip personal data:

```bash
datapm export my-project --redact          # names/emails replaced with [REDACTED]
datapm export --all --redact -o index.json  # redacted full index
```

## License

MIT
