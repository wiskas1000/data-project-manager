"""Enhanced CLI using Typer (optional dependency)."""

import typer

app = typer.Typer(
    name="datapm",
    help="Data Project Manager — launcher and metadata database for analytical work.",
    no_args_is_help=True,
)


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


if __name__ == "__main__":
    app()
