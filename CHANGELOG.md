# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [0.1.0] — 2026-04-07

### Added

- `datapm new` — interactive and one-liner project creation:
  - Generates a dated slug (`YYYY-MM-DD-short-name`) from the project title;
    Unicode characters are transliterated to ASCII
  - Scaffolds a `YYYY-MM-DD_Title/` folder with `archief/`, `communicatie/`,
    and `documenten/` always present; optional groups (`data`, `src`,
    `literatuur`, `resultaten`, `notebooks`) added on request
  - Writes `project.json` to the project folder (DB is source of truth;
    JSON is a one-directional export)
  - Optional `git init` with a minimal `.gitignore`
  - Writes a record to the SQLite database (`~/.datapm/projects.db` by
    default)
- `datapm list` — lists all projects; supports `--status` and `--domain`
  filters; Rich table with colour-coded status when Typer is installed
- `datapm config init [--force]` — creates `~/.datapm/config.json` with
  default project roots, folder preferences, and sensitivity defaults
- SQLite database with version-based migrations; migration 1 creates
  `project` and `project_root` tables
- `ProjectRepository` and `ProjectRootRepository` — Python API for
  create / get / list / update operations on projects and roots
- Two-tier CLI: `cli/app.py` (Typer + Rich) loads when `typer` is
  installed; `cli/fallback.py` (stdlib argparse) is the universal fallback
- Zero runtime dependencies in `core/` and `db/` — only stdlib used
- Config loader with deep-merge: on-disk values override defaults; missing
  keys are filled from `DEFAULT_CONFIG`
- `get_connection(db_path?)` — opens the SQLite file, enables WAL mode
  and foreign keys, and runs migrations automatically

### Infrastructure

- uv-managed project with `pyproject.toml`, `uv.lock`
- Dev dependencies: pytest, pytest-cov, ruff, pre-commit, sphinx,
  sphinx-autodoc-typehints
- pre-commit hooks: `ruff check` (pre-commit) + `uv run pytest` (pre-push)
- 64 passing tests across config, DB, and core layers

---

## [0.0.0] — 2026-04-07

Project bootstrapped: repository structure, `pyproject.toml`, `.gitignore`,
`.pre-commit-config.yaml`, package skeleton, two-tier CLI stubs.
