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
    new_parser.add_argument("--description", help="Free-text description")
    new_parser.add_argument(
        "--type",
        dest="archetype",
        help="Project archetype (minimal, analysis, modeling, "
        "reporting, research, full)",
    )
    new_parser.add_argument(
        "--folder",
        dest="folders",
        action="append",
        metavar="KEY",
        help="Explicit folder key (repeatable, bypasses archetype)",
    )
    new_parser.add_argument(
        "--add",
        action="append",
        metavar="KEY",
        help="Add folder to archetype defaults",
    )
    new_parser.add_argument(
        "--remove",
        action="append",
        metavar="KEY",
        help="Remove folder from archetype defaults",
    )
    git_group = new_parser.add_mutually_exclusive_group()
    git_group.add_argument(
        "--git",
        action="store_true",
        default=None,
        help="Initialise git in src/",
    )
    git_group.add_argument(
        "--no-git",
        action="store_true",
        default=None,
        help="Skip git initialisation",
    )
    new_parser.add_argument(
        "--adhoc",
        action="store_true",
        help="Mark as an ad-hoc request",
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
        "--force",
        action="store_true",
        help="Overwrite existing config",
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

    # -- Collect inputs (prompt for missing) ---------------------------------
    name: str = args.name or _prompt("Project name: ")
    domain: str | None = args.domain or _prompt_optional("Domain (optional): ")
    description: str | None = args.description or _prompt_optional(
        "Description (optional): "
    )

    # -- Resolve archetype and folders ---------------------------------------
    language = get_folder_language()

    if args.folders:
        # Explicit --folder flags bypass archetype entirely
        optional_folders = resolve_folders(args.folders)
        template_key = "custom"
    elif args.archetype:
        # --type given: use archetype, apply --add/--remove
        archetype = get_archetype(args.archetype)
        optional_folders = resolve_folders(
            archetype.folders, add=args.add, remove=args.remove
        )
        template_key = args.archetype
    else:
        # Interactive: archetype picker + folder toggles
        default_key = get_default_template()
        template_key = _prompt_archetype(default_key)
        archetype = get_archetype(template_key)
        optional_folders = resolve_folders(archetype.folders)

        # Show toggles for adjustment
        skip_toggles = args.add is None and args.remove is None
        if skip_toggles:
            optional_folders = _prompt_folder_toggles(optional_folders)
        else:
            optional_folders = resolve_folders(
                archetype.folders, add=args.add, remove=args.remove
            )

    # -- Git init -----------------------------------------------------------
    do_git_init: bool
    if args.git:
        do_git_init = True
    elif args.no_git:
        do_git_init = False
    else:
        config_default = get_git_init_default()
        if config_default is not None:
            do_git_init = config_default
        elif "src" in optional_folders:
            do_git_init = _prompt_bool("Initialise git in src/? [y/N] ")
        else:
            do_git_init = False

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
            template_used=template_key,
            language=language,
        )
    except (FileExistsError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"  Slug    : {result['slug']}")
    print(f"  Path    : {result['project_path']}")
    print(f"  Status  : {result['status']}")
    if result.get("domain"):
        print(f"  Domain  : {result['domain']}")
    if result.get("has_git_repo"):
        print("  Git     : initialised in src/")
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
        slug = p["slug"]
        status = p["status"]
        title = p["title"]
        print(f"{slug:<{col_slug}}  {status:<{col_status}}  {title}")


def _handle_config(
    args: argparse.Namespace,
    config_parser: argparse.ArgumentParser,
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


def _prompt_archetype(default_key: str = "analysis") -> str:
    """Show a numbered archetype menu and return the selected key."""
    from data_project_manager.core.templates import BUILT_IN_ARCHETYPES

    keys = list(BUILT_IN_ARCHETYPES)
    default_idx = keys.index(default_key) + 1 if default_key in keys else 2

    print("\nProject type:")
    for i, key in enumerate(keys, 1):
        arch = BUILT_IN_ARCHETYPES[key]
        marker = "*" if i == default_idx else " "
        print(f"  {marker}[{i}] {arch.label:<12s} ({arch.description})")

    raw = input(f"Select [1-{len(keys)}, default={default_idx}]: ").strip()
    if not raw:
        return keys[default_idx - 1]
    try:
        choice = int(raw)
        if 1 <= choice <= len(keys):
            return keys[choice - 1]
    except ValueError:
        pass
    print(f"  Invalid choice, using default: {default_key}")
    return default_key


def _prompt_folder_toggles(current: list[str]) -> list[str]:
    """Show folder toggles and let the user adjust."""
    from data_project_manager.core.templates import (
        OPTIONAL_FOLDERS,
        SRC_TOGGLES,
        resolve_folders,
    )

    # Display order: top-level folders, then src children indented
    display_order = [f for f in OPTIONAL_FOLDERS if f not in SRC_TOGGLES] + SRC_TOGGLES
    selected = set(current)

    print("\nFolders (enter numbers to toggle, Enter to confirm):")
    for i, key in enumerate(display_order, 1):
        check = "✓" if key in selected else " "
        indent = "  " if key in SRC_TOGGLES else ""
        label = key
        if key in SRC_TOGGLES:
            label = f"{key}/ (in src/)"
        print(f"  [{i}] {check} {indent}{label}")

    raw = input("Toggle [1-6] or Enter: ").strip()
    if not raw:
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
    main()
