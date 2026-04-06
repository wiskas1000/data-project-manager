# Project Plan

## Methodology

**Iterative/Incremental** with flexible milestone cadence. Four milestones to v1.0.0. Each milestone produces a tagged release with a working, usable increment.

### Definition of Done

| Phase | "Done" means |
|-------|-------------|
| Implementation | Code written, public functions have Google-style docstrings, ruff passes |
| Testing | pytest passes, edge cases covered, commands work end-to-end |
| Release | PR merged to main, semver tag applied, CHANGELOG updated |

### Conventions

- **Branches**: `type/short-description`
- **Commits**: `type(scope): description`
- **PRs**: Title mirrors branch. Body: Why + What changed
- **CLI**: Build argparse first, add Typer wrapper per milestone
- **Files**: Only create what the current PR needs

---

## Milestone 1: Launcher — `v0.1.0`

**Summary**: The core product — `datapm new` creates projects with interactive questions, folder scaffolding, metadata, and a SQLite database record. This replaces manual project setup and is immediately usable.

### Acceptance Criteria

- [ ] `python -m data_project_manager config init` creates `~/.datapm/config.json` with a default root
- [ ] `python -m data_project_manager new` interactively asks for project name, domain, and optional folders
- [ ] `python -m data_project_manager new "My Project" --domain healthcare` works as one-liner
- [ ] Creates `YYYY-MM-DD_Project-Name/` with archief/, communicatie/, documenten/
- [ ] Prompts for optional folders (data/, src/, literatuur/, resultaten/, notebooks/)
- [ ] `project.json` is created in the project folder with all metadata
- [ ] SQLite DB is created with `_schema_version` table and Project/ProjectRoot tables
- [ ] Optional git init works when selected
- [ ] `python -m data_project_manager list` shows all projects with status
- [ ] If Typer installed, `datapm new` shows enhanced Rich-formatted interactive flow
- [ ] All tests pass, ruff clean

### Testing Strategy

Unit tests: config loading, slug generation (Unicode, spaces, capitalization), folder creation (verify structure on disk), DB schema creation and migration. Integration test: full `datapm new` flow end-to-end on temp directory.

### Pull Requests (in merge order)

| # | Branch | Size | Description |
|---|--------|------|-------------|
| 1 | `chore/repo-scaffolding` | S | pyproject.toml (zero runtime deps, optional `[enhanced]`), ruff config, pre-commit hooks, .gitignore, `__init__.py` + `__main__.py`, pytest conftest. |
| 2 | `feat/config-system` | M | `config/loader.py`, `config/defaults.py`: JSON config with project roots, defaults. Argparse: `config init`. XDG-aware path (`~/.datapm/`). |
| 3 | `feat/database-foundation` | M | `db/connection.py`: SQLite connection manager (finds DB from config). `db/schema.py`: migration system with `_schema_version` table. Migration 1: Project and ProjectRoot tables only. `db/repositories/project.py`: ProjectRepository with create/get/list/update. |
| 4 | `feat/project-creation` | L | `core/project.py`: `create_project()` — slug generation, folder scaffolding, `project.json` export, git init. Argparse: `new` (interactive + one-liner), `list`. |
| 5 | `feat/enhanced-cli-v1` | M | `cli/app.py`: Typer wrapper for `new`, `list`, `config init`. Rich-formatted project creation flow with interactive prompts. |
| 6 | `docs/v0.1.0-release` | S | README (install via uv and pip, quickstart), CHANGELOG. |

---

## Milestone 2: Full Schema & Library API — `v0.2.0`

**Summary**: All 16 tables exist in the database. All repository classes are available as a Python API. Data pipelines and future integrations can now import and use the repository layer. `datapm info` gives a formatted view of any project's full metadata.

### Acceptance Criteria

- [ ] All 16 tables from ARCHITECTURE.md exist (schema migration 2)
- [ ] Repository classes exist for every entity group with create/get/list/update/delete
- [ ] `from data_project_manager.db.repositories.data_file import DataFileRepository` works
- [ ] A data pipeline script can register a file, a person, a tag via the Python API
- [ ] Person repository supports SCD2 versioning (create_new_version sets valid_to on old record)
- [ ] Basic `datapm project update` command works (status, description, domain, tags)
- [ ] `datapm info <project-slug>` shows all metadata for a project in a formatted view
- [ ] Seed data for common EntityType and AggregationLevel values
- [ ] All repository classes have full test coverage
- [ ] API usage is documented with examples

### Testing Strategy

Unit tests for every repository class: CRUD operations, M:N junction management, Person SCD2 versioning (new version on update, is_current flag, valid_from/valid_to), ChangeLog auto-logging. Integration test: simulate a data pipeline that creates a project, registers files, assigns people — all via Python API.

### Pull Requests (in merge order)

| # | Branch | Size | Description |
|---|--------|------|-------------|
| 1 | `feat/schema-complete` | L | Schema migration 2: all remaining 14 tables (Person with SCD2 fields, Tag, DataFile, Query, Deliverable, RequestQuestion, ChangeLog, EntityType, AggregationLevel, all junction tables). Seed data for lookups. |
| 2 | `feat/repositories-people-tags` | M | `db/repositories/person.py` (Person with SCD2 versioning + ProjectPerson), `db/repositories/tag.py` (Tag + ProjectTag). Full CRUD. Person.create_new_version() sets valid_to on old record, creates new with valid_from. |
| 3 | `feat/repositories-data` | M | `db/repositories/data_file.py` (DataFile + EntityType + AggregationLevel + junctions), `db/repositories/query.py`, `db/repositories/deliverable.py` (+ DeliverableDataFile), `db/repositories/question.py`. |
| 4 | `feat/changelog` | S | `db/repositories/changelog.py`: ChangeLog recording. Hook into repository update methods. |
| 5 | `feat/project-update-info` | S | Argparse: `project update` (status, domain, tags, external_url) and `info <slug>` (formatted metadata view). Validates inputs. |
| 6 | `docs/api-usage` | M | Sphinx autodoc for all repository classes. Usage examples: how a data pipeline imports and writes to the DB. |

---

## Milestone 3: Search & Export — `v0.3.0`

**Summary**: Find projects across the entire history. Export structured JSON for LLM context or downstream tools. This is where the database pays off.

### Acceptance Criteria

- [ ] `python -m data_project_manager search "churn"` finds projects by title, description, tags, domain
- [ ] `python -m data_project_manager search --domain healthcare --status done` filters correctly
- [ ] `python -m data_project_manager search --tag logistic-regression` works
- [ ] `python -m data_project_manager export <project-slug>` outputs clean JSON with all metadata and relationships
- [ ] `python -m data_project_manager export --all` outputs index of all projects
- [ ] JSON export includes related persons, tags, data files, deliverables (whatever exists)
- [ ] Enhanced CLI: Rich tables for search results, syntax-highlighted JSON for export

### Testing Strategy

Unit tests: search query parsing, filter combinations, FTS5 integration. Integration test: create 10+ projects with varied metadata, verify search accuracy. Test JSON export schema structure.

### Pull Requests (in merge order)

| # | Branch | Size | Description |
|---|--------|------|-------------|
| 1 | `feat/search-engine` | L | `core/search.py`: SQLite FTS5 virtual table for text search, structured filters for metadata (domain, status, tags, date range). Schema migration 3: FTS5 table + triggers to keep it in sync. |
| 2 | `feat/search-cli` | M | Argparse: `search` with flags for domain, status, tags, person, date range. Tabular text output. |
| 3 | `feat/json-export` | M | `core/export.py`: export single project or full index as structured JSON. Includes all relationships. Argparse: `export` command. |
| 4 | `feat/enhanced-cli-v3` | M | Typer wrappers for search and export. Rich tables, JSON syntax highlighting, color-coded status/sensitivity. |

---

## Milestone 4: Documentation, Stability & v1 Release — `v1.0.0`

**Summary**: Complete docs, comprehensive tests, cross-platform verification, first stable release.

### Acceptance Criteria

- [ ] Sphinx docs build with full API reference for all repository classes
- [ ] Library usage guide with real examples (data pipeline, export for LLM)
- [ ] All CLI commands have `--help` with examples
- [ ] Test coverage ≥ 85%
- [ ] Cross-platform: tested on Windows + Unix
- [ ] Zero-dep mode verified (uninstall Typer, confirm argparse works)
- [ ] CHANGELOG complete v0.1.0 through v1.0.0
- [ ] README: quickstart, feature overview, library API intro, install instructions

### Testing Strategy

Coverage sweep, edge cases (Unicode slugs, long paths, empty DB), cross-platform path handling, zero-dep mode.

### Pull Requests (in merge order)

| # | Branch | Size | Description |
|---|--------|------|-------------|
| 1 | `docs/full-api-reference` | L | Sphinx autodoc for all modules. Docstring review. Library usage examples in docstrings. |
| 2 | `test/coverage-sweep` | L | Gap analysis, edge cases, cross-platform tests, zero-dep mode, ≥85% coverage. |
| 3 | `docs/user-guide` | M | Quickstart, CLI examples, library API guide, template customization, FAQ. |
| 4 | `chore/v1-release` | S | Final CHANGELOG, version bump, release checklist, tag v1.0.0. |

---

## Summary

| Milestone | Tag | PRs | Focus |
|-----------|-----|-----|-------|
| Launcher | v0.1.0 | 6 | `datapm new`, config, DB foundation |
| Full Schema & Library API | v0.2.0 | 6 | All 16 tables, repository classes (SCD2 Person), Python API, `datapm info` |
| Search & Export | v0.3.0 | 4 | FTS5 search, JSON export, AI readiness |
| Docs & v1 Release | v1.0.0 | 4 | Documentation, coverage, stability |
| **Total** | | **20** | |

## Post v1.0.0 — Build When Needed

These features grow from real usage, not upfront planning:

- **Directory scanner** (`datapm scan`): walk a project folder, find unregistered files, suggest metadata. Could be CLI or web UI.
- **Web dashboard**: local browser UI for reviewing projects, tagging files, managing metadata visually. Imports the same repository classes.
- **Data pipeline hooks**: SQL modules register files they create via the Python API (documented in v0.2.0).
- **Trello/DevOps sync**: populate people and project status from external tools.
- **Email parsing**: auto-populate project metadata from Outlook .msg/.eml files.
- **Purge system**: bulk delete sensitive files past retention with impact analysis.
- **Multi-root polish**: custom templates, `datapm template list`, root management CLI.
