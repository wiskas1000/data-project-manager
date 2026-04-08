# `datapm new` — Folder Selection UX Design

## Context

This document redesigns the interactive folder selection in `datapm new`. Currently the tool prompts yes/no for individual optional folders. The new design introduces **project archetypes** (presets) so the common case is one keystroke, while still allowing per-folder toggles.

### Constraints from ARCHITECTURE.md / CLAUDE.md

- Default folders (always created): `archief/`, `communicatie/`, `documenten/`
- Optional folders: `data/`, `src/`, `literatuur/`, `resultaten/`, `notebooks/`
- `data/` always includes `raw/`, `processed/`, `metadata/` — not independently toggleable
- `src/` includes `queries/` (see Section F for discussion)
- `resultaten/` includes `export/`, `figuren/`
- Folder names default to Dutch, switchable to English via `preferences.folder_language` in config
- Core logic is stdlib-only; Rich/Typer is optional enhancement
- Config lives in `~/.datapm/config.json`

---

## A. Project Archetypes

Archetypes are presets that pre-check optional folders. The three default folders (`archief/`, `communicatie/`, `documenten/`) are always created regardless of archetype.

| Archetype | Key | Optional Folders Included | Typical Use |
|-----------|-----|--------------------------|-------------|
| **Minimal** | `minimal` | _(none)_ | Quick ad-hoc question, no code or data |
| **Analysis** | `analysis` | `data/`, `notebooks/` | Standard analytical work, exploration |
| **Modeling** | `modeling` | `data/`, `src/`, `notebooks/`, `resultaten/` | ML/statistical modeling with deliverables |
| **Reporting** | `reporting` | `data/`, `src/`, `resultaten/` | Recurring reports, dashboards |
| **Research** | `research` | `data/`, `notebooks/`, `literatuur/`, `resultaten/` | Literature-heavy, write-up at end |
| **Full** | `full` | _all optional folders_ | Large or uncertain scope |

### Design decisions

- **`minimal` has zero optional folders** — for the quick "someone asked a question, I answered in 10 minutes" case. The base three folders handle filing emails and docs.
- **`analysis` is the expected default** — most analytical work needs data + notebooks. No `src/` because ad-hoc analysis often stays in notebooks.
- **`resultaten/` appears in archetypes that produce deliverables** — modeling, reporting, research. Not in `analysis` because exploratory work often doesn't produce a formal output.
- **`literatuur/` only defaults on for `research`** — one toggle away for other types.
- **`src/` appears in `modeling` and `reporting`** — where structured, reusable code is expected.

---

## B. Interactive UX Flow

### B.1 Happy path

```
$ datapm new

? Project name: Churn analysis
? Domain: marketing
? Project type:
  ○ Minimal             (no optional folders)
  ❯ Analysis            data, notebooks
    Modeling             data, src, notebooks, resultaten
    Reporting            data, src, resultaten
    Research             data, notebooks, literatuur, resultaten
    Full                 all optional folders

? Optional folders for "Churn analysis" (space to toggle, enter to confirm):
  ✓ data/           raw + processed + metadata
  ○ src/            source code + queries
  ○ literatuur/     reference papers, documentation
  ○ resultaten/     export + figuren
  ✓ notebooks/      Jupyter notebooks

? Initialize git repo? [y/N]: n

✔ Created 2026-04-07_Churn-Analysis/ with 5 folders.
```

Total interactions for the common case: type name → type domain → arrow+enter (archetype) → enter (accept defaults) → enter (no git) → done.

### B.2 Step-by-step breakdown

```
Step 1: Name           Text input (or CLI argument)
Step 2: Domain         Text input (or --domain flag)
Step 3: Archetype      Single-select list
Step 4: Toggle/confirm Multi-select checklist (pre-filled by archetype)
Step 5: Git init       Yes/no (skipped if config has git_init set)
Step 6: Done           Summary line + scaffold
```

### B.3 Shortcut flags (zero-prompt mode)

```bash
# Archetype defaults, no prompts
datapm new "Churn analysis" --domain marketing --type analysis

# Archetype + add/remove specific folders
datapm new "Churn analysis" --domain marketing --type analysis --add literatuur --remove notebooks

# Explicit folder list (bypasses archetypes entirely)
datapm new "Churn analysis" --domain marketing --folder data --folder notebooks

# With git
datapm new "Churn analysis" --domain marketing --type modeling --git

# Custom template from config
datapm new "Churn analysis" --domain marketing --template my-team-standard
```

When `--type`, `--template`, or `--folder` is provided, skip the interactive archetype/toggle steps. When `--git` is provided, skip the git prompt.

### B.4 Plain terminal rendering (argparse fallback)

No arrow keys, no ANSI — works over SSH, in minimal containers, everywhere:

```
Project type:
  [1] Minimal        (no optional folders)
  [2] Analysis       (data, notebooks)
  [3] Modeling       (data, src, notebooks, resultaten)
  [4] Reporting      (data, src, resultaten)
  [5] Research       (data, notebooks, literatuur, resultaten)
  [6] Full           (all optional folders)
Select [1-6, default=2]: 2

Optional folders (enter numbers to toggle, or press Enter to confirm):
  [1] ✓ data/
  [2]   src/
  [3]   literatuur/
  [4]   resultaten/
  [5] ✓ notebooks/
Toggle [1-5] or Enter to confirm:

Initialize git repo? [y/N]:
```

Implementation: plain `input()` calls, zero dependencies. The toggle step accepts comma-separated numbers (`1,3`) or just Enter to accept.

### B.5 Rich terminal rendering (Typer/InquirerPy)

With the `[enhanced]` extra installed, use `InquirerPy` or `questionary` for arrow-key navigation and colored checkboxes. The archetype list shows a brief description on the right. The folder list uses space-to-toggle with visual checkmarks.

Detection logic (already in `__main__.py`):

```python
try:
    from data_project_manager.cli.app import app  # Typer path
except ImportError:
    from data_project_manager.cli.fallback import main  # argparse path
```

### B.6 Git init behavior

- Prompted as a simple yes/no at the end of the flow
- Skipped entirely if `defaults.git_init` is set in config (uses that value silently)
- Overridden by `--git` / `--no-git` flags
- When git init runs: creates `.gitignore` with just `data/` excluded
- The `.gitignore` is intentionally minimal — just `data/` — since projects can be Python, R, Julia, or mixed. Language-specific ignores are the user's responsibility. A richer `.gitignore` generator is a post-v1 feature.

---

## C. Config Schema

All config changes fit within the existing `~/.datapm/config.json` structure from ARCHITECTURE.md.

### C.1 Updated schema

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
      "description": "Our team's standard layout",
      "folders": ["data", "src", "notebooks", "resultaten"]
    },
    "client-delivery": {
      "description": "Client-facing deliverable project",
      "folders": ["data", "src", "resultaten"]
    }
  }
}
```

### C.2 Schema rules

**`defaults.template`** — which archetype is pre-selected in the picker. Accepts built-in keys (`minimal`, `analysis`, `modeling`, `reporting`, `research`, `full`) or custom template names. Default: `"analysis"`.

**`templates.<name>.folders`** — required. List of optional folder keys: `data`, `src`, `literatuur`, `resultaten`, `notebooks`. The three base folders are always created and not listed here.

**`templates.<name>.description`** — optional. Shown next to the template name in the interactive picker.

**`preferences.folder_language`** — `"nl"` (default) or `"en"`. Controls folder names on disk:

| Key | Dutch (nl) | English (en) |
|-----|-----------|-------------|
| _base_ | `archief/` | `archive/` |
| _base_ | `communicatie/` | `communication/` |
| _base_ | `documenten/` | `documents/` |
| `data` | `data/` | `data/` |
| `src` | `src/` | `src/` |
| `literatuur` | `literatuur/` | `literature/` |
| `resultaten` | `resultaten/` | `results/` |
| `notebooks` | `notebooks/` | `notebooks/` |

Subfolder names also translate: `figuren/` → `figures/`, `export/` stays `export/`.

The folder *keys* in archetypes and config are always the Dutch names (canonical). The language preference only affects what gets created on disk. This means `--folder literatuur` and `--add literatuur` work regardless of language setting.

### C.3 Merge / override order

```
Built-in archetypes (hardcoded in core/templates.py)
  ↓ extended by
~/.datapm/config.json  → templates section
  ↓ overridden by
CLI flags (--type, --template, --folder, --add, --remove)
```

Custom templates appear in the picker below built-in archetypes:

```
? Project type:
  ○ Minimal
  ❯ Analysis
    Modeling
    Reporting
    Research
    Full
    ──────────────
    my-team-standard    Our team's standard layout
    client-delivery     Client-facing deliverable project
```

### C.4 Programmatic representation

```python
# core/templates.py — stdlib only

from dataclasses import dataclass

FOLDER_NAMES = {
    "nl": {
        "archief": "archief",
        "communicatie": "communicatie",
        "documenten": "documenten",
        "data": "data",
        "src": "src",
        "literatuur": "literatuur",
        "resultaten": "resultaten",
        "notebooks": "notebooks",
    },
    "en": {
        "archief": "archive",
        "communicatie": "communication",
        "documenten": "documents",
        "data": "data",
        "src": "src",
        "literatuur": "literature",
        "resultaten": "results",
        "notebooks": "notebooks",
    },
}

SUBFOLDER_NAMES = {
    "nl": {"raw": "raw", "processed": "processed", "metadata": "metadata",
           "queries": "queries", "export": "export", "figuren": "figuren"},
    "en": {"raw": "raw", "processed": "processed", "metadata": "metadata",
           "queries": "queries", "export": "export", "figuren": "figures"},
}

# Subfolders created automatically when a parent is included
SUBFOLDERS = {
    "data": ["raw", "processed", "metadata"],
    "src": ["queries"],
    "resultaten": ["export", "figuren"],
}

BASE_FOLDERS = ["archief", "communicatie", "documenten"]
OPTIONAL_FOLDERS = ["data", "src", "literatuur", "resultaten", "notebooks"]


@dataclass
class Archetype:
    key: str
    description: str
    folders: list[str]  # subset of OPTIONAL_FOLDERS


BUILT_IN_ARCHETYPES: dict[str, Archetype] = {
    "minimal":   Archetype("minimal",   "no optional folders", []),
    "analysis":  Archetype("analysis",  "data, notebooks",
                           ["data", "notebooks"]),
    "modeling":  Archetype("modeling",  "data, src, notebooks, resultaten",
                           ["data", "src", "notebooks", "resultaten"]),
    "reporting": Archetype("reporting", "data, src, resultaten",
                           ["data", "src", "resultaten"]),
    "research":  Archetype("research",  "data, notebooks, literatuur, resultaten",
                           ["data", "notebooks", "literatuur", "resultaten"]),
    "full":      Archetype("full",      "all optional folders",
                           OPTIONAL_FOLDERS.copy()),
}
```

---

## D. Implementation Notes

### Where this fits in the codebase

| File | Responsibility |
|------|---------------|
| `core/templates.py` | Archetype definitions, folder name mappings, `SUBFOLDERS` — **new file** |
| `core/project.py` | `create_project()` reads selected archetype + toggles, calls `_scaffold_folders()` |
| `config/loader.py` | Loads custom templates from `config.json`, merges with built-ins |
| `cli/fallback.py` | Argparse: `--type`, `--folder`, `--add`, `--remove`, `--git` flags + numbered-menu interactive flow |
| `cli/app.py` | Typer: same flags, Rich-formatted picker and toggle list |

### Milestone alignment

This work fits into **Milestone 1 (v0.1.0), PR #4 (`feat/project-creation`)**. The archetype system replaces the current per-folder yes/no prompts. Custom templates in config can land in the same PR or be split into a small follow-up.

---

## E. Migration from Current Behavior

The old flow (auto-create base folders, yes/no for each optional folder) maps to choosing an archetype and then toggling. Users who always picked the same set of folders can set `defaults.template` in config and skip the picker entirely with `--type`.

No breaking change to the folder structure on disk — the same folders are created, just selected differently.

---

## F. Open Questions

### `src/queries/` — keep or rethink?

Currently `src/` auto-creates `queries/`. This works for SQL-heavy projects, but for Python/R modeling projects the query files often live alongside other source code. Options:

1. **Keep as-is** — `src/queries/` is created when `src/` is selected. Simple, no harm if unused.
2. **Drop the subdirectory** — just create `src/`. Users `mkdir queries` if needed.
3. **Make it configurable** — add a `subfolders` override in custom templates.

Recommendation: **option 1** for v0.1.0. The subdirectory costs nothing and is easy to remove. Revisit if it feels wrong in practice.

### Language default

Current design defaults to Dutch (`"nl"`). This matches the existing codebase. English is one config change away. No per-project language override for v0.1.0 — a global switch covers the 99% case.

### Default archetype

The design defaults to `analysis`. Should this be `minimal` instead to match the "fast deployment" philosophy? The difference is one arrow-key press, so impact is small. Setting `defaults.template` in config resolves this per-user.

### `.gitignore` scope

Current design: when git init runs, create a `.gitignore` containing only `data/`. This prevents accidentally committing large data files while staying language-agnostic. A richer `.gitignore` generator (Python-specific, R-specific, etc.) is a post-v1 feature — for now, users add their own patterns.
