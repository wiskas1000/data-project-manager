# `datapm new` — Folder Selection UX Design

> **Status**: Final draft — ready for implementation  
> **Milestone**: v0.2.0 (folder selection redesign)  
> **Last updated**: 2026-04-08

## 1. Context

This document redesigns the interactive folder selection in `datapm new`.
The current flow prompts for space-separated folder names. The new design
introduces **project archetypes** (presets) so the common case takes a few
keystrokes, while still allowing per-folder toggles.

### Constraints

- Core logic is stdlib-only; Rich/Typer is optional enhancement
- Config lives in `~/.datapm/config.json`
- Folder names default to Dutch, switchable via `preferences.folder_language`
- Git lives inside `src/` (not the project root) — see Section 6
- Projects may live in OneDrive-synced directories

---

## 2. Folder Inventory

### 2.1 Base folders (always created)

| Folder | Role |
|--------|------|
| `communicatie/` | Emails, meeting notes, correspondence |
| `documenten/` | **Input** artifacts — Word docs, Excel files, specs, briefs people send you |

These two are created for every project, every archetype.

### 2.2 `archief/` — never created at project start

`archief/` is an **end-of-lifecycle** folder for completed or superseded
files. Creating it at project start adds clutter. It is created later by:

- `mkdir archief/` (manual)
- A future `datapm archive <project>` command (post-v1)

No archetype includes `archief/`.

### 2.3 Optional folders

| Folder | Role | Notes |
|--------|------|-------|
| `data/` | Data files | Always includes `raw/`, `processed/`, `metadata/` |
| `src/` | Source code, scripts | Git repo root (see Section 6) |
| `src/notebooks/` | Marimo / Jupyter notebooks | Toggleable; selecting it implies `src/` |
| `src/queries/` | SQL files | Toggleable; selecting it implies `src/` |
| `literatuur/` | Reference papers, articles, external reports | Background reading, not project-specific input |
| `resultaten/` | **Output** artifacts | Always includes `export/`, `figuren/` |

### 2.4 Folder role clarification

The three "document" folders serve distinct roles:

- **`documenten/`** = things other people give you for this project
  (requirements, data dictionaries, Excel specs, Word briefs)
- **`resultaten/`** = things you produce for others (dashboards, report
  PDFs, export spreadsheets, generated figures)
- **`literatuur/`** = reference material you read for context (academic
  papers, methodology articles, industry reports — not project-specific
  input)

Decision rule: "Did someone send this to me for this project?" →
`documenten/`. "Am I reading this for background?" → `literatuur/`.
"Did I produce this?" → `resultaten/`.

### 2.5 Subdirectory summary

| Parent | Auto-created children | Independently toggleable? |
|--------|-----------------------|--------------------------|
| `data/` | `raw/`, `processed/`, `metadata/` | No — atomic |
| `src/` | _(empty by default)_ | Yes — `notebooks/` and `queries/` are toggles |
| `resultaten/` | `export/`, `figuren/` | No — atomic |

### 2.6 Notebooks live inside `src/`

Notebooks are source code. Since `src/` is the git boundary, notebooks
belong under version control alongside scripts:

```
src/
├── .git/
├── .gitignore
├── notebooks/        ← Marimo / Jupyter
├── queries/          ← SQL files
└── *.py              ← Python scripts
```

In the interactive UX, `notebooks` appears as a visible toggle. Selecting
it implicitly enables `src/`. Toggling `src/` off also disables
`notebooks` and `queries`.

---

## 3. Project Archetypes

Archetypes pre-fill the folder toggles. Base folders (`communicatie/`,
`documenten/`) are always created on top.

| Archetype | Key | Optional Folders | Typical Use |
|-----------|-----|------------------|-------------|
| **Minimal** | `minimal` | _(none)_ | Quick ad-hoc question, no code or data |
| **Analysis** | `analysis` | `data`, `src`, `notebooks`, `resultaten` | Standard analytical work — **the default** |
| **Modeling** | `modeling` | `data`, `src`, `notebooks`, `resultaten`, `literatuur` | ML / statistical modeling |
| **Reporting** | `reporting` | `data`, `src`, `queries`, `resultaten` | Recurring reports, scheduled queries |
| **Research** | `research` | `data`, `src`, `notebooks`, `literatuur`, `resultaten` | Literature-heavy, exploratory |
| **Full** | `full` | _all optional folders_ | Large or uncertain scope |

### Design decisions

- **`analysis` is the default.** Most analytical work needs data +
  notebooks + results. `src/queries/` is off because not every analysis
  uses standalone SQL files.
- **`modeling` includes `literatuur/`** because ML work typically involves
  reading papers about methods and benchmarks.
- **`reporting` includes `queries/` but not `notebooks/`** because
  reporting is typically scheduled SQL + scripts, not interactive
  notebooks.
- **`research` mirrors `modeling`** but without `queries/` — more
  notebook-driven, less SQL-driven.
- **All archetypes except `minimal` include `data/`, `src/`, and
  `resultaten/`.** These are the backbone of any code-involving project.
- **`archief/` is never in any archetype.**

### Example: modeling project on disk

```
2026-04-08_Churn-Model/
├── communicatie/
├── documenten/           ← model requirements, evaluation criteria
├── data/
│   ├── raw/              ← source datasets
│   ├── processed/        ← feature-engineered data, train/test splits
│   └── metadata/         ← data dictionaries, schema docs
├── src/
│   ├── .git/
│   ├── .gitignore
│   ├── notebooks/        ← EDA, model iteration, evaluation
│   └── *.py              ← training scripts, pipelines
├── literatuur/           ← papers on methods, benchmark results
├── resultaten/
│   ├── export/           ← model predictions, scored datasets
│   └── figuren/          ← ROC curves, feature importance, confusion matrices
└── project.json
```

Model artifacts (`.pkl`, `.joblib`, saved weights) go in
`data/processed/` for now. A dedicated `models/` subfolder can be added
later if the pattern emerges.

---

## 4. Interactive UX Flow

### 4.1 Happy path (Rich terminal)

```
$ datapm new

? Project name: Churn analysis
? Domain (optional): marketing
? Description (optional): Q2 churn drivers for retail segment
? Project type:
  ○ Minimal             communicatie, documenten
  ❯ Analysis            + data, src, notebooks, resultaten
    Modeling             + data, src, notebooks, resultaten, literatuur
    Reporting            + data, src, queries, resultaten
    Research             + data, src, notebooks, literatuur, resultaten
    Full                 all folders

? Folders (space to toggle, enter to confirm):
  ✓ data/               raw + processed + metadata
  ✓ src/                source code
  ✓   src/notebooks/    Marimo / Jupyter notebooks
  ○   src/queries/      SQL files
  ○ literatuur/         reference papers, articles
  ✓ resultaten/         export + figuren

? Initialise git in src/? [y/N]: y

✔ Created 2026-04-08_Churn-Analysis/ with 6 folders.
```

### 4.2 Plain terminal rendering (argparse fallback)

```
Project type:
  [1] Minimal        (communicatie, documenten)
  [2] Analysis       (+ data, src, notebooks, resultaten)
  [3] Modeling       (+ data, src, notebooks, resultaten, literatuur)
  [4] Reporting      (+ data, src, queries, resultaten)
  [5] Research       (+ data, src, notebooks, literatuur, resultaten)
  [6] Full           (all folders)
Select [1-6, default=2]:

Folders (enter numbers to toggle, Enter to confirm):
  [1] ✓ data/
  [2] ✓ src/
  [3] ✓   notebooks/ (in src/)
  [4]     queries/   (in src/)
  [5]   literatuur/
  [6] ✓ resultaten/
Toggle [1-6] or Enter:

Initialise git in src/? [y/N]:
```

Accepts comma-separated numbers (`1,3`) or Enter to accept defaults.

### 4.3 Shortcut flags (zero-prompt mode)

```bash
# Archetype defaults, no prompts
datapm new "Churn analysis" --domain marketing --type analysis

# Add/remove from archetype
datapm new "Churn analysis" --type analysis --add queries --remove notebooks

# Explicit folder list (bypasses archetypes)
datapm new "Churn analysis" --folder data --folder src --folder resultaten

# With git
datapm new "Churn analysis" --type analysis --git

# Custom template from config
datapm new "Churn analysis" --template my-team-standard
```

When `--type`, `--template`, or `--folder` is provided, skip the
interactive archetype/toggle steps. When `--git` / `--no-git` is
provided, skip the git prompt.

### 4.4 Step-by-step breakdown

| Step | Prompt | Skipped when |
|------|--------|-------------|
| 1 | Project name | Provided as CLI argument |
| 2 | Domain (optional) | `--domain` flag |
| 3 | Description (optional) | `--description` flag |
| 4 | Archetype picker | `--type`, `--template`, or `--folder` |
| 5 | Folder toggles | `--type` without `--add`/`--remove`, or `--folder` |
| 6 | Git init | `--git`/`--no-git`, or `defaults.git_init` in config |
| 7 | Done | _(always shown)_ |

---

## 5. Config Schema

All changes fit within the existing `~/.datapm/config.json` structure.

### 5.1 Updated schema

```json
{
  "general": {
    "default_root": "work"
  },
  "roots": {
    "work": { "path": "/home/user/projects/work" },
    "personal": { "path": "/home/user/projects/personal" }
  },
  "defaults": {
    "template": "analysis",
    "git_init": false,
    "sensitivity": "internal"
  },
  "preferences": {
    "folder_language": "nl"
  },
  "templates": {
    "my-team-standard": {
      "description": "Standard team layout",
      "folders": ["data", "src", "notebooks", "queries", "resultaten"]
    }
  }
}
```

### 5.2 Schema rules

**`defaults.template`** — pre-selected archetype in the picker. Accepts
built-in keys (`minimal`, `analysis`, `modeling`, `reporting`, `research`,
`full`) or custom template names. Default: `"analysis"`.

**`defaults.git_init`** — when set, skips the git prompt and uses this
value. When absent, the user is prompted.

**`templates.<name>.folders`** — required. List of optional folder keys:
`data`, `src`, `notebooks`, `queries`, `literatuur`, `resultaten`. Keys
`notebooks` and `queries` are `src/` children — including either one
implicitly includes `src/`.

**`templates.<name>.description`** — optional. Shown in the picker.

**`preferences.folder_language`** — `"nl"` (default) or `"en"`:

| Key | Dutch (`nl`) | English (`en`) |
|-----|-------------|---------------|
| _base_ | `communicatie/` | `communication/` |
| _base_ | `documenten/` | `documents/` |
| _archive_ | `archief/` | `archive/` |
| `data` | `data/` | `data/` |
| `src` | `src/` | `src/` |
| `notebooks` | `src/notebooks/` | `src/notebooks/` |
| `queries` | `src/queries/` | `src/queries/` |
| `literatuur` | `literatuur/` | `literature/` |
| `resultaten` | `resultaten/` | `results/` |

Subfolder names also translate: `figuren/` → `figures/`.

Folder **keys** in archetypes, config, and CLI flags are always the Dutch
names (canonical). The language setting only affects what is created on
disk. `--folder literatuur` works regardless of language setting.

### 5.3 Custom templates in picker

Custom templates from config appear below built-in archetypes:

```
? Project type:
  ○ Minimal
  ❯ Analysis
    Modeling
    Reporting
    Research
    Full
    ──────────────
    my-team-standard    Standard team layout
```

### 5.4 Override order

```
Built-in archetypes (hardcoded in core/templates.py)
  ↓ extended by
~/.datapm/config.json → templates section
  ↓ overridden by
CLI flags (--type, --template, --folder, --add, --remove)
```

---

## 6. Git Initialisation

### 6.1 Git lives in `src/`

The project root often lives in a OneDrive-synced directory. OneDrive
and git conflict — OneDrive syncs `.git/` internals during operations,
causing lock conflicts and corrupted pack files. Placing git inside
`src/` solves this:

- **OneDrive** syncs the whole project folder. `src/` (or just
  `src/.git/`) is excluded from OneDrive sync (one-time per-project
  setting).
- **Git** only tracks source code — notebooks, queries, scripts.
- **No conflict** — each system owns its own files.

Colleagues access `documenten/`, `resultaten/`, `communicatie/` via
OneDrive. They never need to touch `src/`.

```
2026-04-08_Churn-Analysis/          ← OneDrive-synced
├── communicatie/                    ← synced
├── documenten/                     ← synced
├── data/                           ← synced
├── resultaten/                     ← synced
├── src/                            ← excluded from OneDrive
│   ├── .git/
│   ├── .gitignore
│   ├── notebooks/
│   └── *.py
└── project.json                    ← synced
```

### 6.2 `.gitignore` content

Minimal and language-agnostic. Users add their own patterns:

```gitignore
# datapm default — add language-specific patterns as needed
__pycache__/
*.pyc
.ipynb_checkpoints/
```

### 6.3 Behaviour

- Prompted: "Initialise git in src/?" (yes/no)
- Skipped if `defaults.git_init` is set in config
- Overridden by `--git` / `--no-git` flags
- Requires `src/` to be selected — if `src/` is off, git prompt is
  skipped entirely
- Sets `has_git_repo` on the Project DB record

### 6.4 Editor configuration note

Since `.git/` lives in `src/` rather than the project root, editors
that walk up the tree for `.git/` (nvim, VS Code) will only find the
repo when working within `src/`. When coding, open your editor rooted
at `src/`. For project-wide file browsing, use your file manager or
a separate terminal.

A future `datapm` enhancement could generate a workspace config file
(`.nvim.lua`, `.vscode/settings.json`) that points to `src/.git/`.
This is post-v1.

---

## 7. Programmatic Representation

```python
# core/templates.py — stdlib only

from dataclasses import dataclass

FOLDER_NAMES: dict[str, dict[str, str]] = {
    "nl": {
        "communicatie": "communicatie",
        "documenten": "documenten",
        "archief": "archief",
        "data": "data",
        "src": "src",
        "literatuur": "literatuur",
        "resultaten": "resultaten",
    },
    "en": {
        "communicatie": "communication",
        "documenten": "documents",
        "archief": "archive",
        "data": "data",
        "src": "src",
        "literatuur": "literature",
        "resultaten": "results",
    },
}

SUBFOLDER_NAMES: dict[str, dict[str, str]] = {
    "nl": {
        "raw": "raw",
        "processed": "processed",
        "metadata": "metadata",
        "queries": "queries",
        "notebooks": "notebooks",
        "export": "export",
        "figuren": "figuren",
    },
    "en": {
        "raw": "raw",
        "processed": "processed",
        "metadata": "metadata",
        "queries": "queries",
        "notebooks": "notebooks",
        "export": "export",
        "figuren": "figures",
    },
}

# Auto-created when parent is selected (not independently toggleable)
SUBFOLDERS: dict[str, list[str]] = {
    "data": ["raw", "processed", "metadata"],
    "resultaten": ["export", "figuren"],
}

# src/ sub-items that ARE independently toggleable
SRC_TOGGLES: list[str] = ["notebooks", "queries"]

BASE_FOLDERS: list[str] = ["communicatie", "documenten"]

OPTIONAL_FOLDERS: list[str] = [
    "data", "src", "notebooks", "queries", "literatuur", "resultaten",
]
# "notebooks" and "queries" are src/ children but listed as top-level
# toggles for UX. Selecting either implies src/.


@dataclass
class Archetype:
    """A project archetype defining default optional folders."""

    key: str
    description: str
    folders: list[str]  # subset of OPTIONAL_FOLDERS


BUILT_IN_ARCHETYPES: dict[str, Archetype] = {
    "minimal": Archetype(
        "minimal",
        "communicatie, documenten",
        [],
    ),
    "analysis": Archetype(
        "analysis",
        "+ data, src, notebooks, resultaten",
        ["data", "src", "notebooks", "resultaten"],
    ),
    "modeling": Archetype(
        "modeling",
        "+ data, src, notebooks, resultaten, literatuur",
        ["data", "src", "notebooks", "literatuur", "resultaten"],
    ),
    "reporting": Archetype(
        "reporting",
        "+ data, src, queries, resultaten",
        ["data", "src", "queries", "resultaten"],
    ),
    "research": Archetype(
        "research",
        "+ data, src, notebooks, literatuur, resultaten",
        ["data", "src", "notebooks", "literatuur", "resultaten"],
    ),
    "full": Archetype(
        "full",
        "all folders",
        OPTIONAL_FOLDERS.copy(),
    ),
}
```

---

## 8. Implementation Notes

### Files to create or modify

| File | Change |
|------|--------|
| `core/templates.py` | **New** — archetype definitions, folder/subfolder mappings (Section 7) |
| `core/project.py` | Update `create_project()` to accept archetype key + toggle overrides; update `_scaffold_folders()` to use template system |
| `config/loader.py` | Load custom templates from config, merge with built-ins |
| `cli/fallback.py` | Add `--type`, `--add`, `--remove`, `--git`/`--no-git` flags; numbered-menu interactive flow |
| `cli/app.py` | Rich-formatted archetype picker + folder toggle list |

### Toggle dependencies

```
notebooks ON  → src ON (implicit)
queries ON    → src ON (implicit)
src OFF       → notebooks OFF, queries OFF (forced)
git init      → requires src ON (else skipped)
```

---

## 9. Migration from Current Behaviour

The current flow (space-separated folder names) maps to choosing an
archetype and optionally toggling folders. Changes visible to the user:

- **`archief/` is no longer auto-created** — the only breaking change.
  Existing projects are unaffected.
- **`notebooks/` moves from top-level to `src/notebooks/`** — new
  projects only. Existing projects keep their structure.
- **Interactive flow changes** from free-text folder input to
  archetype picker + toggles.

---

## 10. Future Work (post-v1)

These are noted here for context but are **not in scope** for v0.1.0:

- **`datapm archive <project>`** — creates `archief/`, moves specified
  files, sets status to `archived`
- **`datapm sync <project>`** — copies `src/` (without `.git/`) to the
  OneDrive project folder as a snapshot, so colleagues can see code
  without git access
- **Editor workspace generation** — `datapm init-editor` creates
  `.nvim.lua` or `.vscode/settings.json` pointing to `src/.git/`
- **Rich `.gitignore` generator** — language-specific patterns (Python,
  R, Julia) based on project contents
- **`models/` subfolder** — for ML projects with significant model
  artifacts; add as a `data/` or `src/` child once the pattern is clear
