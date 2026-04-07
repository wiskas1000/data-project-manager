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
    help="Data Project Manager — launcher and metadata database for analytical work.",
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
    folders: Annotated[
        list[str] | None,
        typer.Option("--folder", help="Optional folder group (repeatable)"),
    ] = None,
    git: Annotated[bool, typer.Option("--git", help="Run git init")] = False,
    description: Annotated[
        str | None, typer.Option(help="Free-text description")
    ] = None,
    adhoc: Annotated[bool, typer.Option("--adhoc", help="Mark as ad-hoc")] = False,
) -> None:
    """Create a new project (interactive or one-liner)."""
    from data_project_manager.core.project import OPTIONAL_FOLDER_KEYS, create_project

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

    optional_folders: list[str] = folders or []
    if not folders:
        _console.print(f"[dim]Optional folders:[/] {', '.join(OPTIONAL_FOLDER_KEYS)}")
        raw = typer.prompt(
            "Add folders? (space-separated, or Enter to skip)", default=""
        )
        if raw.strip():
            optional_folders = [k for k in raw.split() if k in OPTIONAL_FOLDER_KEYS]

    do_git: bool = git or typer.confirm("Initialise git repo?", default=False)

    _console.print()
    _console.print(f"Creating project [bold]{project_name}[/] …")

    try:
        result = create_project(
            project_name,
            domain=project_domain,
            description=project_description,
            is_adhoc=adhoc,
            optional_folders=optional_folders,
            do_git_init=do_git,
        )
    except FileExistsError as exc:
        _err_console.print(f"[bold red]Error:[/] {exc}")
        sys.exit(1)

    # -- Success summary panel -----------------------------------------------
    rows = [
        ("Slug", result["slug"]),
        ("Path", result["project_path"]),
        ("Status", result["status"]),
    ]
    if result.get("domain"):
        rows.append(("Domain", result["domain"]))
    if result.get("has_git_repo"):
        rows.append(("Git", "initialised"))

    summary = "\n".join(f"[dim]{label:<8}[/]  {value}" for label, value in rows)
    _console.print(Panel(summary, title="[bold green]Project created[/]", expand=False))


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

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
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
def search(query: Annotated[str, typer.Argument(help="Search query")]) -> None:
    """Search projects by metadata."""
    _console.print(f"Searching for: [bold]{query}[/]")


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------


@config_app.command("init")
def config_init(
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite existing config")
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


if __name__ == "__main__":
    app()
