# Architecture

## System Overview

Data Project Manager is a launcher, schema owner, and Python library for managing analytical project metadata.

```
┌─────────────────────────────────────────────────────┐
│              Consumers (post v1.0.0)                 │
│   Data pipelines · Scanner · Web dashboard · Sync   │
├─────────────────────────────────────────────────────┤
│              CLI Layer (two-tier)                    │
│   Enhanced: Typer + Rich (if available)             │
│   Fallback: argparse (stdlib, always works)         │
│   Commands: new, list, info, search, export, config │
├─────────────────────────────────────────────────────┤
│          Core Library (stdlib only)                  │
│   Project creation · Search · Export · Slug gen      │
├─────────────────────────────────────────────────────┤
│       Repository Layer (stdlib sqlite3)             │
│   Python API: one class per entity group             │
│   Primary interface for all consumers                │
├─────────────────────────────────────────────────────┤
│              SQLite Database                         │
│   16 entities · FTS5 search · version-based DDL      │
├─────────────────────────────────────────────────────┤
│              Config + Exports                        │
│   ~/.datapm/config.json                      │
│   Per-project project.json (one-directional export)  │
└─────────────────────────────────────────────────────┘
```

### Layer Responsibilities

**Consumers**: External systems that read/write the database via the repository layer. Data pipelines register files they create. A scanner finds unregistered files. A web UI provides visual management. These are post-v1.0.0 — the repository API is their interface.

**CLI Layer**: Two-tier. `cli/fallback.py` (argparse, stdlib) is built first and works everywhere. `cli/app.py` (Typer + Rich) wraps the same core functions with prettier output. Auto-detected at runtime. Limited to launcher, search, and export commands — not a manual data entry tool.

**Core Library**: Business logic — project creation, slug generation, search, export. **Stdlib only.** Returns dicts and dataclasses. Raises domain exceptions.

**Repository Layer**: Clean Python API over raw SQL. One class per entity group in `db/repositories/`. This is the primary interface for all consumers — CLI, pipelines, scanner, web UI all use the same repository classes.

**SQLite Database**: Source of truth. Single file, portable, zero-config. FTS5 for full-text search. Version-based migrations in `schema.py`.

**Config + Exports**: JSON config in `~/.datapm/config.json` for roots and preferences. Per-project `project.json` is a **one-directional export** (DB → JSON) created on project creation and refreshable via `datapm export`. Not a sync mechanism.

## Data Model

### Entity Summary

| Category | Entity | v1.0.0 CLI | v1.0.0 Library API | Purpose |
|----------|--------|------------|---------------------|---------|
| Core | Project | `datapm new`, `datapm list`, `datapm project update` | ProjectRepository | Central entity |
| Core | ProjectRoot | `datapm config init` | ProjectRepository | Filesystem root |
| Core | Person | — | PersonRepository | People (SCD2 — tracks changes over time) |
| Core | Tag | `datapm project update --tag` | TagRepository | Freeform labels |
| Core | DataFile | — | DataFileRepository | Registered data files |
| Core | Query | — | QueryRepository | SQL/Python/R queries |
| Core | Deliverable | — | DeliverableRepository | Output artifacts |
| Core | RequestQuestion | — | QuestionRepository | Questions from requestors |
| Lookup | EntityType | — | DataFileRepository | What data describes |
| Lookup | AggregationLevel | — | DataFileRepository | Data granularity |
| Audit | ChangeLog | — | ChangeLogRepository | Field-level audit trail |
| Junction | ProjectPerson | — | PersonRepository | M:N project ↔ person |
| Junction | ProjectTag | via `datapm project update` | TagRepository | M:N project ↔ tag |
| Junction | DeliverableDataFile | — | DeliverableRepository | M:N deliverable ↔ file |
| Junction | DataFileEntityType | — | DataFileRepository | M:N file ↔ entity type |
| Junction | DataFileAggregation | — | DataFileRepository | M:N file ↔ agg level |

Entities marked "—" in the CLI column have no CLI commands in v1.0.0. They are populated via the Python library API by data pipelines, scanners, or future integrations.

### Entity-Relationship Diagram

```
                    ┌──────────────┐
                    │ Person(SCD2) │
                    └──────┬───────┘
                           │ 1:N
                    ┌──────┴───────┐
                    │ProjectPerson │
                    └──────┬───────┘
                           │ N:1
┌─────────┐  1:N   ┌──────┴───────┐  1:N   ┌──────────────┐
│   Tag   ├────────┤              ├────────┤  Deliverable  │
└─────────┘        │              │        └──────┬────────┘
     │ 1:N         │   Project    │               │ 1:N
┌────┴────┐        │              │        ┌──────┴────────┐
│ProjectTag│       │              │        │DeliverableData│
└─────────┘        └──┬───┬───┬───┘        │    File       │
                      │   │   │            └──────┬────────┘
                 N:1  │   │   │ 1:N               │ N:1
          ┌───────────┘   │   └──────────┐  ┌─────┘
          │               │ 1:N          │  │
   ┌──────┴──────┐  ┌─────┴──────┐  ┌───┴──┴──────┐
   │ProjectRoot  │  │  Request   │  │  DataFile    │
   │             │  │  Question  │  │              │
   └─────────────┘  └────────────┘  └──┬───┬───┬───┘
                                       │   │   │
                                  1:N  │   │   │ 1:N
                          ┌────────────┘   │   └────────────┐
                          │           1:N  │                 │
                   ┌──────┴──────┐  ┌──────┴───────┐  ┌─────┴──────────┐
                   │DataFileEnti-│  │DataFileAggre-│  │    Query       │
                   │  tyType     │  │   gation     │  │                │
                   └──────┬──────┘  └──────┬───────┘  └────────────────┘
                          │ N:1            │ N:1
                   ┌──────┴──────┐  ┌──────┴───────┐
                   │ EntityType  │  │ Aggregation  │
                   │  (lookup)   │  │ Level(lookup)│
                   └─────────────┘  └──────────────┘

                   ┌─────────────┐
                   │ ChangeLog   │  (logs changes to any entity)
                   └─────────────┘
```

### Entity Definitions

#### Project

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| slug | TEXT | Auto-generated: `YYYY-MM-DD-short-name` |
| title | TEXT | Human-readable |
| description | TEXT | Free-text |
| status | TEXT | active, paused, done, archived |
| is_adhoc | BOOL | Quick ask vs planned work |
| domain | TEXT | Subject area |
| root_id | UUID FK | → ProjectRoot |
| external_url | TEXT | DevOps/Trello link |
| request_date | DATE | When received |
| expected_start | DATE | Planned start |
| expected_end | DATE | Planned end |
| realized_start | DATE | Actual start |
| realized_end | DATE | Actual end |
| estimated_hours | REAL | Effort estimate |
| relative_path | TEXT | Folder path relative to root |
| has_git_repo | BOOL | Whether git init ran |
| template_used | TEXT | Which scaffold template |
| created_at | TEXT | ISO timestamp |
| updated_at | TEXT | ISO timestamp |

#### ProjectRoot

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| name | TEXT | Label (work, personal) |
| absolute_path | TEXT | Full path |
| is_default | BOOL | Active default |
| created_at | TEXT | ISO timestamp |

#### Person (SCD Type 2)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key (unique per version) |
| first_name | TEXT | Given name |
| last_name | TEXT | Family name |
| email | TEXT | Email |
| function_title | TEXT | Job title |
| department | TEXT | Department |
| valid_from | TEXT | ISO date — when this version became active |
| valid_to | TEXT | ISO date — when superseded (NULL = current) |
| is_current | BOOL | Convenience flag (TRUE for latest version) |
| created_at | TEXT | ISO timestamp |

Uses Slowly Changing Dimension Type 2. When a person changes department or role, a new version is created with updated `valid_from`. The old record gets `valid_to` set and `is_current = FALSE`. This tracks role changes across employers over time.

#### ProjectPerson

| Field | Type | Notes |
|-------|------|-------|
| project_id | UUID FK | → Project |
| person_id | UUID FK | → Person |
| role | TEXT | requestor, responder, reviewer, stakeholder |

Composite PK: (project_id, person_id, role). Same person can hold multiple roles.

#### Tag

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| name | TEXT | Unique, normalized lowercase |
| category | TEXT | Optional grouping |

#### ProjectTag

| Field | Type | Notes |
|-------|------|-------|
| project_id | UUID FK | → Project |
| tag_id | UUID FK | → Tag |

#### DataFile

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| project_id | UUID FK | → Project |
| file_path | TEXT | Relative to project root |
| file_format | TEXT | csv, xlsx, parquet, etc. |
| sensitivity | TEXT | public, internal, client_confidential, personal |
| is_source | BOOL | Source vs derived |
| data_period_from | TEXT | ISO date |
| data_period_to | TEXT | ISO date |
| retention_date | TEXT | When to purge (NULL = no auto-purge) |
| purged_at | TEXT | Soft-delete marker |
| created_at | TEXT | ISO timestamp |

#### EntityType / AggregationLevel (Lookups)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| name | TEXT | e.g. customers, daily |

#### DataFileEntityType / DataFileAggregation (Junctions)

| Field | Type |
|-------|------|
| data_file_id | UUID FK |
| entity_type_id / agg_level_id | UUID FK |

#### Query

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| output_file_id | UUID FK | → DataFile produced |
| source_file_id | UUID FK | → DataFile consumed (nullable) |
| query_path | TEXT | Path to query file |
| language | TEXT | SQL, Python, R, DAX |
| sensitivity | TEXT | Inherits or overrides |
| executed_at | TEXT | ISO timestamp |

#### Deliverable

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| project_id | UUID FK | → Project |
| type | TEXT | presentation, report, dashboard, spreadsheet, data_file |
| file_path | TEXT | Relative to project |
| file_format | TEXT | pptx, pdf, xlsx, etc. |
| version | TEXT | e.g. v1, v2-final |
| delivered_at | TEXT | When delivered |
| created_at | TEXT | ISO timestamp |

#### DeliverableDataFile

| Field | Type |
|-------|------|
| deliverable_id | UUID FK |
| data_file_id | UUID FK |

#### RequestQuestion

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| project_id | UUID FK | → Project |
| question_text | TEXT | The question |
| data_period_from | TEXT | ISO date |
| data_period_to | TEXT | ISO date |

#### ChangeLog

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | Primary key |
| entity_type | TEXT | Which table changed |
| entity_id | UUID | Which record |
| field_name | TEXT | Which field |
| old_value | TEXT | Previous value |
| new_value | TEXT | New value |
| changed_at | TEXT | ISO timestamp |

## Sensitivity Model

Four mutually exclusive levels at the **file** level:

| Level | Meaning |
|-------|---------|
| public | No restrictions |
| internal | Organization-internal |
| client_confidential | Client data, contractually restricted |
| personal | Private notes, not visible to employer |

## Project Scaffold

Default template (every project):

```
YYYY-MM-DD_Project-Name/
├── archief/
├── communicatie/
├── documenten/
├── project.json
└── .gitignore          (if git init selected)
```

Optional add-ons (prompted during `datapm new`):

```
├── data/ (with raw/, processed/, metadata/)
├── src/ (with queries/)
├── literatuur/
├── resultaten/ (with export/, figuren/)
└── notebooks/
```

## Configuration

`~/.datapm/config.json`:

```json
{
  "general": {
    "default_root": "work"
  },
  "roots": {
    "work": {
      "path": "/home/user/projects/work"
    },
    "personal": {
      "path": "/home/user/projects/personal"
    }
  },
  "defaults": {
    "template": "minimal",
    "git_init": true,
    "sensitivity": "internal"
  },
  "preferences": {
    "folder_language": "nl"
  }
}
```

## CLI Commands (v1.0.0)

| Command | Description |
|---------|-------------|
| `datapm new` | Create a new project (interactive or one-liner) |
| `datapm list` | List all projects with status |
| `datapm info` | Show all metadata for a project |
| `datapm project update` | Update status, domain, tags, external_url |
| `datapm search` | Search across all projects by metadata |
| `datapm export` | Export project metadata as structured JSON |
| `datapm config init` | Initialize config file |

## Post v1.0.0 Features

- Directory scanner (CLI or web UI)
- Web dashboard for visual file management
- Data pipeline integration hooks
- Trello/DevOps/Jira sync
- Email parsing
- Purge system with impact analysis
- Multi-root management CLI
- Custom template engine
