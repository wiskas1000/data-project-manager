"""Enhanced CLI using Typer (optional dependency)."""

import sys

import typer

app = typer.Typer(
    name="datapm",
    help="Data Project Manager — launcher and metadata database for analytical work.",
    no_args_is_help=True,
)

config_app = typer.Typer(help="Manage configuration.")
app.add_typer(config_app, name="config")


@app.command()
def new(
    name: str = typer.Argument(None, help="Project name"),
    domain: str = typer.Option(None, help="Subject area"),
) -> None:
    """Create a new project."""
    typer.echo(f"Creating project: {name} (domain={domain})")


@app.command()
def search(query: str = typer.Argument(..., help="Search query")) -> None:
    """Search projects by metadata."""
    typer.echo(f"Searching for: {query}")


@config_app.command("init")
def config_init(
    force: bool = typer.Option(False, "--force", help="Overwrite existing config"),
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
