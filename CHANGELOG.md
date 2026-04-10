# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [1.1.1] — 2026-04-10

### Added

- **`--redact` flag** on `datapm export` — replaces names and emails with
  `[REDACTED]` in JSON output. Works in both Rich and argparse CLIs.
- **Privacy section** in README documenting that the database contains
  personal data.

### Fixed

- Folder toggle display: `src/notebooks/` and `src/queries/` now appear
  directly below `src/` instead of at the bottom of the list.
- Folder toggle dependency: deselecting `src/` cascades to subfolders;
  selecting a subfolder auto-selects `src/`.

---

## [1.1.0] — 2026-04-10

### Added

- **Interactive arrow-key pickers** for archetype selection and folder
  toggles in `datapm new` — both Rich/Typer and argparse fallback CLIs.
- **3-second confirmation countdown** after folder selection with Enter to
  skip and Esc/q to abort.
- Number quick-pick (1–6) alongside arrow navigation in archetype picker.

### Fixed

- Rich `MarkupError` when displaying non-default archetypes (empty style
  tags `[][/]`).
- Tests now skip gracefully when Typer is not installed.

### Changed

- UX documentation updated: FOLDER-SELECTION-DESIGN.md, CLI reference,
  quickstart, templates guide, and FAQ.

---

## [1.0.0] — 2026-04-09

### Added

- **Full user documentation**: quickstart guide, CLI reference with examples
  for all commands, template/folder customisation guide, FAQ, and updated
  library usage guide with dataclass attribute access.
- **94% test coverage** (up from 72%): 351 tests across all layers including
  Typer CLI, argparse fallback, entry points, config edge cases, and
  git-init/root-resolution paths.
- **Sphinx docs build clean** with `-W` (warnings-as-errors): full API
  reference for all modules, usage guides, and cross-referenced type docs.

### Changed

- README expanded with all features (search, export, project update, info),
  archetype table, library usage with dataclass examples, and documentation
  links.
- Version bumped to 1.0.0.

---

## [0.3.0] — 2026-04-09

### Added

- **FTS5 full-text search**: schema migration 3 adds a `project_fts` virtual
  table with INSERT/UPDATE/DELETE triggers to keep it in sync.
- **`datapm search`**: find projects by free text (title, description, slug,
  domain) and structured filters (`--domain`, `--status`, `--tag`,
  `--from`/`--to` date range). All filters are combinable.
- **`datapm export`**: export a single project or the full index as structured
  JSON, including tags, people, data files, deliverables, and questions.
  Flags: `--all`, `--output/-o` (write to file), `--compact` (minified).
- **SearchResult** frozen dataclass in `db/models/search.py`.
- Enhanced Typer CLI: Rich tables with description snippets for search,
  syntax-highlighted JSON for export.
- 50 new tests (search engine, search CLI, export, export CLI).

---

## [0.2.1] — 2026-04-09

### Changed

- **Typed data model**: all 16 repository classes now return frozen
  `dataclasses` instead of plain `dict[str, Any]`. New `db/models/`
  package with one file per entity (Project, Person, Tag, DataFile,
  Deliverable, Query, RequestQuestion, ChangeLogEntry, and composite
  types PersonWithRole, ProjectPersonLink).
- Each model has a `from_row()` classmethod for `sqlite3.Row` conversion
  and proper `bool` coercion for SQLite integer flags.
- `db/models/__init__.py` re-exports all 13 types for convenience:
  `from data_project_manager.db.models import Project, Person, Tag`
- Eliminated all 16 `# type: ignore[return-value]` comments across
  repositories.
- CLI handlers updated from `project["id"]` to `project.id` style
  throughout both Typer and argparse implementations.

---

## [0.2.0] — 2026-04-09

### Added

- Schema migration 2: all remaining 14 tables (Person with SCD2 fields,
  Tag, DataFile, Query, Deliverable, RequestQuestion, ChangeLog,
  EntityType, AggregationLevel, and all junction tables). Seed data for
  common entity types and aggregation levels.
- Repository classes for every entity group: `person.py` (Person SCD2 +
  ProjectPerson), `tag.py` (Tag + ProjectTag), `data_file.py` (DataFile +
  EntityType + AggregationLevel + junctions), `deliverable.py`,
  `query.py`, `question.py`, `changelog.py`.
- ChangeLog audit trail: field-level change recording hooked into
  `ProjectRepository.update()` and `PersonRepository.create_new_version()`
  via optional constructor injection.
- `datapm project update <slug>` — update status, domain, description,
  external URL, add/remove tags.
- `datapm info <slug>` — formatted metadata view with tags, people,
  and change history.
- Sphinx autodoc for all 8 repository files. Library usage guide
  (`docs/usage/library.rst`) with full data-pipeline example.
- Shared `_helpers.py` module with `now_iso()` and `row_to_dict()`
  extracted from all repository files.
- Shared `tests/helpers.py` with `fresh_conn()` and `make_project()`
  test utilities.
- 215 passing tests across all layers.

### Changed

- Folder selection redesigned: archetype picker (minimal, analysis,
  modeling, reporting, research, full) with interactive folder toggles.
  Dutch canonical names. Git init moved to `src/` for OneDrive
  compatibility. `archief/` removed from auto-created folders.
- Custom templates supported via `config.json`.

### Fixed

- Slug collision now raises a user-friendly `ValueError` (#14)
- DB connections properly closed with `try/finally` pattern (#15)
- `ProjectRepository.update()` validates column whitelist (#16)
- Sphinx docstring indentation warning in `db.schema` (#17)

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
