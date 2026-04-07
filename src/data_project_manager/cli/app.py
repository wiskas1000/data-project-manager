"""Enhanced CLI using Typer (optional dependency)."""

import sys
from typing import Annotated

import typer

app = typer.Typer(
    name="datapm",
    help="Data Project Manager — launcher and metadata database for analytical work.",
    no_args_is_help=True,
)

config_app = typer.Typer(help="Manage configuration.")
app.add_typer(config_app, name="config")


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
        typer.echo(f"Optional folders: {', '.join(OPTIONAL_FOLDER_KEYS)}")
        raw = typer.prompt(
            "Add folders? (space-separated, or Enter to skip)", default=""
        )
        if raw.strip():
            optional_folders = [k for k in raw.split() if k in OPTIONAL_FOLDER_KEYS]

    do_git: bool = git or typer.confirm("Initialise git repo?", default=False)

    typer.echo()
    typer.echo(f"Creating project '{project_name}' …")

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
        typer.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    typer.echo(f"  Slug    : {result['slug']}")
    typer.echo(f"  Path    : {result['project_path']}")
    typer.echo(f"  Status  : {result['status']}")
    if result.get("domain"):
        typer.echo(f"  Domain  : {result['domain']}")
    typer.echo("\nDone.")


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
        typer.echo("No projects found.")
        return

    col_slug = max(len(p["slug"]) for p in projects)
    col_status = max(len(p["status"]) for p in projects)
    col_slug = max(col_slug, 4)
    col_status = max(col_status, 6)

    header = f"{'SLUG':<{col_slug}}  {'STATUS':<{col_status}}  TITLE"
    typer.echo(header)
    typer.echo("-" * len(header))
    for p in projects:
        typer.echo(
            f"{p['slug']:<{col_slug}}  {p['status']:<{col_status}}  {p['title']}"
        )


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@app.command()
def search(query: Annotated[str, typer.Argument(help="Search query")]) -> None:
    """Search projects by metadata."""
    typer.echo(f"Searching for: {query}")


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
        typer.echo(f"Config initialised at {path}")
    except FileExistsError as exc:
        typer.echo(f"Error: {exc}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    app()
