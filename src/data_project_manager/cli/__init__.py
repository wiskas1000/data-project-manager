"""CLI package — two-tier entry point.

The :func:`main` function is the single entry point used by both the
``datapm`` console script and ``python -m data_project_manager``.  It
tries to load the Typer-based enhanced CLI; if Typer is not installed it
falls back to the stdlib argparse CLI.
"""


def main() -> None:
    """Run the CLI, choosing Typer or argparse at runtime."""
    try:
        import typer as _typer  # noqa: F401 — probe only
    except ImportError:
        from data_project_manager.cli.fallback import main as _main

        _main()
        return

    from data_project_manager.cli.app import app

    app()
