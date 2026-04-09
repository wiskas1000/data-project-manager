"""Enhanced CLI using Typer + Rich (optional dependency)."""

import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    name="datapm",
    help=("Data Project Manager — launcher and metadata database for analytical work."),
    no_args_is_help=True,
)

config_app = typer.Typer(help="Manage configuration.")
app.add_typer(config_app, name="config")

project_app = typer.Typer(help="Manage project metadata.")
app.add_typer(project_app, name="project")

_console = Console()
_err_console = Console(stderr=True)

# Colour mapping for project status values.
_STATUS_STYLE: dict[str, str] = {
    "active": "bold green",
    "paused": "yellow",
    "done": "bold blue",
    "archived": "dim",
}


def _status_text(status: str) -> Text:
    """Return a Rich :class:`~rich.text.Text` styled for *status*."""
    return Text(status, style=_STATUS_STYLE.get(status, ""))


# ---------------------------------------------------------------------------
# new
# ---------------------------------------------------------------------------


@app.command()
def new(
    name: Annotated[str | None, typer.Argument(help="Project name")] = None,
    domain: Annotated[str | None, typer.Option(help="Subject area")] = None,
    description: Annotated[
        str | None, typer.Option(help="Free-text description")
    ] = None,
    archetype: Annotated[
        str | None,
        typer.Option(
            "--type",
            help="Project archetype (minimal, analysis, modeling, "
            "reporting, research, full)",
        ),
    ] = None,
    folders: Annotated[
        list[str] | None,
        typer.Option("--folder", help="Explicit folder key (repeatable)"),
    ] = None,
    add: Annotated[
        list[str] | None,
        typer.Option("--add", help="Add folder to archetype defaults"),
    ] = None,
    remove: Annotated[
        list[str] | None,
        typer.Option("--remove", help="Remove folder from archetype defaults"),
    ] = None,
    git: Annotated[
        bool | None,
        typer.Option("--git/--no-git", help="Initialise git in src/"),
    ] = None,
    adhoc: Annotated[bool, typer.Option("--adhoc", help="Mark as ad-hoc")] = False,
) -> None:
    """Create a new project (interactive or one-liner)."""
    from data_project_manager.config.loader import (
        get_default_template,
        get_folder_language,
        get_git_init_default,
    )
    from data_project_manager.core.project import create_project
    from data_project_manager.core.templates import (
        get_archetype,
        resolve_folders,
    )

    # -- Collect inputs ------------------------------------------------------
    project_name: str = name or typer.prompt("Project name")
    project_domain: str | None = domain
    if project_domain is None:
        raw = typer.prompt("Domain (optional)", default="")
        project_domain = raw.strip() or None
    project_description: str | None = description
    if project_description is None:
        raw = typer.prompt("Description (optional)", default="")
        project_description = raw.strip() or None

    # -- Resolve archetype and folders ---------------------------------------
    language = get_folder_language()

    if folders:
        # Explicit --folder flags bypass archetype entirely
        optional_folders = resolve_folders(folders)
        template_key = "custom"
    elif archetype:
        # --type given: use archetype, apply --add/--remove
        arch = get_archetype(archetype)
        optional_folders = resolve_folders(arch.folders, add=add, remove=remove)
        template_key = archetype
    else:
        # Interactive: archetype picker + folder toggles
        default_key = get_default_template()
        template_key = _prompt_archetype_rich(default_key)
        arch = get_archetype(template_key)
        optional_folders = resolve_folders(arch.folders)

        # Show toggles for adjustment
        if add is None and remove is None:
            optional_folders = _prompt_folder_toggles_rich(optional_folders)
        else:
            optional_folders = resolve_folders(arch.folders, add=add, remove=remove)

    # -- Git init -----------------------------------------------------------
    do_git_init: bool
    if git is True:
        do_git_init = True
    elif git is False:
        do_git_init = False
    else:
        config_default = get_git_init_default()
        if config_default is not None:
            do_git_init = config_default
        elif "src" in optional_folders:
            do_git_init = typer.confirm("Initialise git in src/?", default=False)
        else:
            do_git_init = False

    _console.print()
    _console.print(f"Creating project [bold]{project_name}[/] …")

    try:
        result = create_project(
            project_name,
            domain=project_domain,
            description=project_description,
            is_adhoc=adhoc,
            optional_folders=optional_folders,
            do_git_init=do_git_init,
            template_used=template_key,
            language=language,
        )
    except (FileExistsError, ValueError) as exc:
        _err_console.print(f"[bold red]Error:[/] {exc}")
        sys.exit(1)

    # -- Success summary panel -----------------------------------------------
    rows = [
        ("Slug", result["slug"]),
        ("Path", result["project_path"]),
        ("Status", result["status"]),
        ("Template", result.get("template_used", "")),
    ]
    if result.get("domain"):
        rows.append(("Domain", result["domain"]))
    if result.get("has_git_repo"):
        rows.append(("Git", "initialised in src/"))

    summary = "\n".join(f"[dim]{label:<10}[/]  {value}" for label, value in rows)
    _console.print(
        Panel(
            summary,
            title="[bold green]Project created[/]",
            expand=False,
        )
    )


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@app.command(name="list")
def list_cmd(
    status: Annotated[str | None, typer.Option(help="Filter by status")] = None,
    domain: Annotated[str | None, typer.Option(help="Filter by domain")] = None,
) -> None:
    """List all projects."""
    from data_project_manager.core.project import list_projects

    projects = list_projects(status=status, domain=domain)

    if not projects:
        _console.print("[dim]No projects found.[/]")
        return

    table = Table(
        show_header=True,
        header_style="bold",
        box=None,
        pad_edge=False,
    )
    table.add_column("Slug", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Domain", style="dim")
    table.add_column("Title")

    for p in projects:
        table.add_row(
            p["slug"],
            _status_text(p["status"]),
            p.get("domain") or "",
            p["title"],
        )

    _console.print(table)


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


@app.command()
def info(
    slug: Annotated[str, typer.Argument(help="Project slug")],
) -> None:
    """Show all metadata for a project."""
    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.changelog import ChangeLogRepository
    from data_project_manager.db.repositories.person import ProjectPersonRepository
    from data_project_manager.db.repositories.project import ProjectRepository
    from data_project_manager.db.repositories.tag import ProjectTagRepository

    conn = get_connection()
    try:
        project = ProjectRepository(conn).get_by_slug(slug)
        if project is None:
            _err_console.print(f"[bold red]Error:[/] project '{slug}' not found.")
            raise typer.Exit(1)

        pid = project["id"]
        tags = ProjectTagRepository(conn).list_for_project(pid)
        people = ProjectPersonRepository(conn).list_for_project(pid)
        log = ChangeLogRepository(conn).list_for_entity("project", pid)

        # Core fields table
        table = Table(box=None, pad_edge=False, show_header=False)
        table.add_column(style="dim", no_wrap=True)
        table.add_column()

        field_rows = [
            ("Slug", project["slug"]),
            ("Status", _status_text(project["status"])),
            ("Domain", project.get("domain") or ""),
            ("Description", project.get("description") or ""),
            ("Template", project.get("template_used") or ""),
            ("Git", "yes" if project.get("has_git_repo") else "no"),
            ("Path", project.get("relative_path") or ""),
            ("Request date", project.get("request_date") or ""),
            ("Expected start", project.get("expected_start") or ""),
            ("Expected end", project.get("expected_end") or ""),
            ("Realized start", project.get("realized_start") or ""),
            ("Realized end", project.get("realized_end") or ""),
            ("Est. hours", str(project.get("estimated_hours") or "")),
        ]
        for label, value in field_rows:
            if value and str(value):
                table.add_row(label, value)

        _console.print(
            Panel(
                table,
                title=f"[bold]{project['title']}[/]",
                expand=False,
            )
        )

        # Tags
        if tags:
            tag_names = ", ".join(f"[cyan]{t['name']}[/]" for t in tags)
            _console.print(f"[dim]Tags:[/] {tag_names}")

        # People
        if people:
            _console.print("[dim]People:[/]")
            for p in people:
                full = f"{p['first_name']} {p['last_name']}"
                _console.print(f"  {full:<24} [dim]{p['role']}[/]")

        # Change log
        if log:
            _console.print("[dim]Change log (last 5):[/]")
            for entry in log[-5:]:
                ts = entry["changed_at"][:19]
                field = entry["field_name"]
                old = entry["old_value"] or "[dim]—[/]"
                new = entry["new_value"] or "[dim]—[/]"
                _console.print(f"  [dim]{ts}[/]  {field:<16}  {old} → {new}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# project update
# ---------------------------------------------------------------------------


@project_app.command("update")
def project_update(
    slug: Annotated[str, typer.Argument(help="Project slug")],
    status: Annotated[
        str | None, typer.Option(help="New status (active/paused/done/archived)")
    ] = None,
    domain: Annotated[str | None, typer.Option(help="Subject area")] = None,
    description: Annotated[
        str | None, typer.Option(help="Free-text description")
    ] = None,
    external_url: Annotated[
        str | None, typer.Option("--external-url", help="DevOps/Trello URL")
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Add a tag (repeatable)"),
    ] = None,
    remove_tags: Annotated[
        list[str] | None,
        typer.Option("--remove-tag", help="Remove a tag (repeatable)"),
    ] = None,
) -> None:
    """Update mutable fields on a project."""
    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.changelog import ChangeLogRepository
    from data_project_manager.db.repositories.project import ProjectRepository
    from data_project_manager.db.repositories.tag import (
        ProjectTagRepository,
        TagRepository,
    )

    conn = get_connection()
    try:
        changelog = ChangeLogRepository(conn)
        repo = ProjectRepository(conn, changelog=changelog)

        project = repo.get_by_slug(slug)
        if project is None:
            _err_console.print(f"[bold red]Error:[/] project '{slug}' not found.")
            raise typer.Exit(1)

        pid = project["id"]

        # Validate and collect scalar updates
        updates: dict = {}
        if status is not None:
            valid = {"active", "paused", "done", "archived"}
            if status not in valid:
                _err_console.print(
                    f"[bold red]Error:[/] invalid status '{status}'. "
                    f"Must be one of {sorted(valid)}."
                )
                raise typer.Exit(1)
            updates["status"] = status
        if domain is not None:
            updates["domain"] = domain
        if description is not None:
            updates["description"] = description
        if external_url is not None:
            updates["external_url"] = external_url

        if updates:
            repo.update(pid, **updates)

        # Tag operations
        tag_repo = TagRepository(conn)
        pt_repo = ProjectTagRepository(conn)
        for name in tags or []:
            tag = tag_repo.create(name=name)
            pt_repo.add(project_id=pid, tag_id=tag["id"])
        for name in remove_tags or []:
            tag = tag_repo.get_by_name(name)
            if tag:
                pt_repo.remove(project_id=pid, tag_id=tag["id"])

        if not updates and not tags and not remove_tags:
            _console.print("[dim]Nothing to update.[/]")
            return

        _console.print(f"[bold green]✓[/] Updated [cyan]{slug}[/]")
        for key, new_val in updates.items():
            old_val = project[key]
            _console.print(f"  [dim]{key}:[/] {old_val} → [bold]{new_val}[/]")
        for name in tags or []:
            _console.print(f"  [dim]tag added:[/] [cyan]{name}[/]")
        for name in remove_tags or []:
            _console.print(f"  [dim]tag removed:[/] [cyan]{name}[/]")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query")],
) -> None:
    """Search projects by metadata."""
    _console.print(f"Searching for: [bold]{query}[/]")


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------


@config_app.command("init")
def config_init(
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite existing config"),
    ] = False,
) -> None:
    """Create ~/.datapm/config.json with defaults."""
    from data_project_manager.config.loader import init_config

    try:
        path = init_config(force=force)
        _console.print(f"[bold green]✓[/] Config initialised at [cyan]{path}[/]")
    except FileExistsError as exc:
        _err_console.print(f"[bold red]Error:[/] {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Rich interactive helpers
# ---------------------------------------------------------------------------


def _prompt_archetype_rich(default_key: str = "analysis") -> str:
    """Show a Rich-formatted archetype picker."""
    from data_project_manager.core.templates import BUILT_IN_ARCHETYPES

    keys = list(BUILT_IN_ARCHETYPES)
    default_idx = keys.index(default_key) + 1 if default_key in keys else 2

    _console.print("\n[bold]Project type:[/]")
    for i, key in enumerate(keys, 1):
        arch = BUILT_IN_ARCHETYPES[key]
        if i == default_idx:
            marker = "[bold cyan]❯[/]"
            style = "bold"
        else:
            marker = " "
            style = ""
        _console.print(
            f"  {marker} [{style}]{arch.label:<12s}[/{style}]"
            f"  [dim]{arch.description}[/]"
        )

    raw = typer.prompt(f"Select [1-{len(keys)}]", default=str(default_idx))
    try:
        choice = int(raw)
        if 1 <= choice <= len(keys):
            return keys[choice - 1]
    except ValueError:
        pass
    return default_key


def _prompt_folder_toggles_rich(current: list[str]) -> list[str]:
    """Show Rich-formatted folder toggles."""
    from data_project_manager.core.templates import (
        OPTIONAL_FOLDERS,
        SRC_TOGGLES,
        resolve_folders,
    )

    display_order = [f for f in OPTIONAL_FOLDERS if f not in SRC_TOGGLES] + SRC_TOGGLES
    selected = set(current)

    _console.print(
        "\n[bold]Folders[/] [dim](enter numbers to toggle, Enter to confirm):[/]"
    )
    for i, key in enumerate(display_order, 1):
        check = "[green]✓[/]" if key in selected else "[dim]○[/]"
        indent = "    " if key in SRC_TOGGLES else ""
        label = f"src/{key}/" if key in SRC_TOGGLES else f"{key}/"
        _console.print(f"  [{i}] {check} {indent}{label}")

    raw = typer.prompt("Toggle or Enter", default="")
    if not raw.strip():
        return sorted(selected)

    for token in raw.replace(",", " ").split():
        try:
            idx = int(token) - 1
            if 0 <= idx < len(display_order):
                key = display_order[idx]
                if key in selected:
                    selected.discard(key)
                else:
                    selected.add(key)
        except ValueError:
            continue

    return resolve_folders(sorted(selected))


if __name__ == "__main__":
    app()
