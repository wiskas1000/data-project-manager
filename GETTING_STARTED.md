# Getting Started with Claude Code

## Pre-requisites

1. Install `gh` (GitHub CLI) and authenticate with repo and project scopes:
   `gh auth login -s repo,project`
2. Install `uv`
3. Make sure git is configured for this repo (after step 4): `git config user.name "Your Name"` and `git config user.email "you@example.com"` (no `--global` — keeps it local to this repo)
4. Create an empty directory, `cd` into it
5. Copy `CLAUDE.md` + `docs/` folder with `ARCHITECTURE.md`, `PLAN.md`, `TECH_STACK.md`

## What Claude Code will do on GitHub

Claude Code uses `git` and `gh` CLI to manage the full workflow. When it asks for permission, these are the operations it will perform:

- **Git**: `init`, `add`, `commit`, `checkout -b`, `push -u origin`, `tag`, `merge`
- **GitHub (via `gh`)**: `repo create`, `pr create`, `pr merge`, `issue create`
- **GitHub API (via `gh api`)**: create/close milestones, create/manage project board, link issues and PRs to project

All of these require the `repo` and `project` scopes from step 1. If Claude Code gets a permission error, run `gh auth refresh -s repo,project` to re-authorize.

## Session 1a: Create repo and scaffold

```
Read CLAUDE.md, docs/ARCHITECTURE.md, and docs/PLAN.md.

Bootstrap the project on main:

1. git init (if not already initialised)
2. gh repo create data-project-manager --public --source=. --push
3. uv init, configure pyproject.toml per CLAUDE.md:
   - name: data_project_manager, requires-python >=3.11
   - dependencies = [] (zero runtime deps)
   - [project.optional-dependencies] enhanced = ["typer[all]"]
   - CLI entry point: datapm = "data_project_manager.cli:main"
   - [tool.ruff] and [tool.pytest.ini_options] per CLAUDE.md
4. uv add --dev pytest pytest-cov ruff pre-commit sphinx sphinx-autodoc-typehints
5. uv add --optional enhanced "typer[all]"
6. Create .gitignore, .pre-commit-config.yaml
7. Create package skeleton: only __init__.py files + __main__.py + conftest.py
8. Create __main__.py with two-tier CLI detection
9. Create minimal cli/app.py (Typer) and cli/fallback.py (argparse)

Follow CLAUDE.md. Use uv exclusively. No placeholder files.
```

## Session 1b: Verify, push, and set up GitHub Project

```
Verify everything works:

1. uv run pre-commit install && uv run pre-commit install --hook-type pre-push
2. uv run ruff check . && uv run ruff format --check .
3. uv run pytest → passes
4. uv run datapm --help → Typer help
5. uv run python -m data_project_manager --help → argparse help

Commit and push:

6. git add -A && git commit -m "chore(repo): initialize project structure"
7. git tag -a v0.0.0 -m "Project bootstrap"
8. git push origin main --tags

Set up GitHub Project board:

9. Create a GitHub Project (kanban board) linked to the repo:
   gh project create --owner @me --title "Data Project Manager" --format board
10. Note the project number returned (e.g., 1). Use it in subsequent commands.

Create milestone and issues for v0.1.0:

11. Create milestone:
    gh api repos/{owner}/{repo}/milestones -f title="v0.1.0 — Launcher" -f description="Config system, database schema, and datapm new command"
12. Create issues for all v0.1.0 PRs from PLAN.md, assigned to the milestone:
    For each PR in PLAN.md v0.1.0:
      gh issue create --title "[branch-name]" --body "[PR description from PLAN.md]" --milestone "v0.1.0 — Launcher"
13. Add all created issues to the GitHub Project:
    For each issue number:
      gh project item-add [project-number] --owner @me --url https://github.com/{owner}/{repo}/issues/[number]
```

## Session 2+: Feature PRs

```
Read CLAUDE.md and docs/PLAN.md.

Milestone [v0.X.0], PR: `[branch-name]`.

1. git checkout main && git pull origin main
2. git checkout -b [branch-name]
3. Implement per PLAN.md: [paste description]
4. Conventions: small commits, docstrings, tests, stdlib-only in core/db
5. Verify: ruff, pytest, datapm --help
6. git push -u origin [branch-name]
7. gh pr create --title "[branch-name]" --body "## Why\n...\n## What changed\n...\n\nCloses #[issue-number]" --milestone "..."
8. Add the PR to the GitHub Project:
   gh project item-add [project-number] --owner @me --url [PR url]
9. Show me what to review.
```

## Merging

```
gh pr merge [branch-name] --squash --delete-branch
git checkout main && git pull origin main
```

## Milestone completion

```
All PRs for [v0.X.0] merged. Finalize:

1. Update CHANGELOG.md
2. git commit -am "docs(changelog): add v0.X.0 release notes"
3. git tag -a v0.X.0 -m "Milestone: [Title]"
4. git push origin main --tags
5. Close the milestone:
   gh api repos/{owner}/{repo}/milestones/[number] -X PATCH -f state=closed
6. Create next milestone and its issues from PLAN.md
7. Add new issues to the GitHub Project:
   gh project item-add [project-number] --owner @me --url [issue url]
```

## Tips

- Review every PR diff before merging
- After v0.1.0, use it on a real project before building v0.2.0
- After v0.1.0, add GitHub Actions CI as a `chore/github-actions` PR — a single `.github/workflows/ci.yml` that runs `ruff check` + `pytest` on every PR. Don't set it up during bootstrap.
- Test zero-dep mode: uninstall typer, run `python -m data_project_manager --help`
- PLAN.md is the source of truth — update it if scope changes
- The GitHub Project board auto-tracks PR status (open → merged) once items are linked
- CLAUDE.md and GETTING_STARTED.md stay on main — they're dev docs, not shipped code
