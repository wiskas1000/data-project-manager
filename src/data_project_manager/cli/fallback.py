"""Fallback CLI using stdlib argparse (zero dependencies)."""

import argparse
import sys


def main() -> None:
    """Entry point for the argparse-based CLI."""
    parser = argparse.ArgumentParser(
        prog="datapm",
        description=(
            "Data Project Manager — launcher and metadata database for analytical work."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    # new
    new_parser = subparsers.add_parser("new", help="Create a new project")
    new_parser.add_argument("name", nargs="?", help="Project name")
    new_parser.add_argument("--domain", help="Subject area")

    # search
    search_parser = subparsers.add_parser("search", help="Search projects by metadata")
    search_parser.add_argument("query", help="Search query")

    # config
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_sub = config_parser.add_subparsers(dest="config_command")
    config_init = config_sub.add_parser(
        "init", help="Create ~/.datapm/config.json with defaults"
    )
    config_init.add_argument(
        "--force", action="store_true", help="Overwrite existing config"
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
    elif args.command == "new":
        print(f"Creating project: {args.name} (domain={args.domain})")
    elif args.command == "search":
        print(f"Searching for: {args.query}")
    elif args.command == "config":
        _handle_config(args, config_parser)


def _handle_config(
    args: argparse.Namespace, config_parser: argparse.ArgumentParser
) -> None:
    """Dispatch config sub-commands."""
    if args.config_command is None:
        config_parser.print_help()
        return

    if args.config_command == "init":
        from data_project_manager.config.loader import init_config

        try:
            path = init_config(force=args.force)
            print(f"Config initialised at {path}")
        except FileExistsError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
