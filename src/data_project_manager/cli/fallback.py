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
    new_parser.add_argument(
        "--folders",
        nargs="*",
        metavar="FOLDER",
        help="Optional folder groups to add (data src literatuur resultaten notebooks)",
    )
    new_parser.add_argument(
        "--git", action="store_true", help="Run git init in the project folder"
    )
    new_parser.add_argument("--description", help="Free-text description")
    new_parser.add_argument(
        "--adhoc", action="store_true", help="Mark as an ad-hoc request"
    )

    # list
    list_parser = subparsers.add_parser("list", help="List all projects")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--domain", help="Filter by domain")

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
        _handle_new(args)
    elif args.command == "list":
        _handle_list(args)
    elif args.command == "search":
        print(f"Searching for: {args.query}")
    elif args.command == "config":
        _handle_config(args, config_parser)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _handle_new(args: argparse.Namespace) -> None:
    """Interactive or one-liner project creation."""
    from data_project_manager.core.project import (
        OPTIONAL_FOLDER_KEYS,
        create_project,
    )

    # -- Collect inputs (prompt for missing) ---------------------------------
    name: str = args.name or _prompt("Project name: ")
    domain: str | None = args.domain or _prompt_optional("Domain (optional): ")
    description: str | None = args.description or _prompt_optional(
        "Description (optional): "
    )

    # Optional folders — only prompt interactively when none given via CLI
    optional_folders: list[str] = args.folders or []
    if not args.folders and args.folders is not None:
        # --folders was passed with no values: skip interactive prompt
        optional_folders = []
    elif args.folders is None:
        # --folders was not passed at all: interactive
        optional_folders = _prompt_folders(OPTIONAL_FOLDER_KEYS)

    do_git_init: bool = args.git or _prompt_bool("Initialise git repo? [y/N] ")

    print()
    print(f"Creating project '{name}' …")

    try:
        result = create_project(
            name,
            domain=domain,
            description=description,
            is_adhoc=args.adhoc,
            optional_folders=optional_folders,
            do_git_init=do_git_init,
        )
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"  Slug    : {result['slug']}")
    print(f"  Path    : {result['project_path']}")
    print(f"  Status  : {result['status']}")
    if result.get("domain"):
        print(f"  Domain  : {result['domain']}")
    print("\nDone.")


def _handle_list(args: argparse.Namespace) -> None:
    """Print a table of projects."""
    from data_project_manager.core.project import list_projects

    projects = list_projects(status=args.status, domain=args.domain)

    if not projects:
        print("No projects found.")
        return

    col_slug = max(len(p["slug"]) for p in projects)
    col_status = max(len(p["status"]) for p in projects)
    col_slug = max(col_slug, 4)
    col_status = max(col_status, 6)

    header = f"{'SLUG':<{col_slug}}  {'STATUS':<{col_status}}  TITLE"
    print(header)
    print("-" * len(header))
    for p in projects:
        print(f"{p['slug']:<{col_slug}}  {p['status']:<{col_status}}  {p['title']}")


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


# ---------------------------------------------------------------------------
# Interactive prompt helpers
# ---------------------------------------------------------------------------


def _prompt(message: str) -> str:
    """Prompt for a required non-empty string."""
    while True:
        value = input(message).strip()
        if value:
            return value
        print("  (value required)")


def _prompt_optional(message: str) -> str | None:
    """Prompt for an optional value; return ``None`` if blank."""
    value = input(message).strip()
    return value if value else None


def _prompt_bool(message: str) -> bool:
    """Prompt for a yes/no answer (default no)."""
    return input(message).strip().lower() in {"y", "yes"}


def _prompt_folders(keys: list[str]) -> list[str]:
    """Prompt the user to choose optional folder groups."""
    print(f"Optional folders ({', '.join(keys)}):")
    print("  Enter names separated by spaces, or press Enter to skip.")
    raw = input("  > ").strip()
    if not raw:
        return []
    chosen = [k for k in raw.split() if k in keys]
    unknown = [k for k in raw.split() if k not in keys]
    if unknown:
        print(f"  Ignoring unknown keys: {unknown}")
    return chosen


if __name__ == "__main__":
    main()
