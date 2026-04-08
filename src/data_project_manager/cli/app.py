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
