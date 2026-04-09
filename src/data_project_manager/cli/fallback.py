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

    # info
    info_parser = subparsers.add_parser("info", help="Show all metadata for a project")
    info_parser.add_argument("slug", help="Project slug")

    # project
    project_parser = subparsers.add_parser("project", help="Manage project metadata")
    project_sub = project_parser.add_subparsers(dest="project_command")
    project_update = project_sub.add_parser("update", help="Update project metadata")
    project_update.add_argument("slug", help="Project slug")
    project_update.add_argument(
        "--status", help="New status (active/paused/done/archived)"
    )
    project_update.add_argument("--domain", help="Subject area")
    project_update.add_argument("--description", help="Free-text description")
    project_update.add_argument(
        "--external-url", dest="external_url", help="DevOps/Trello URL"
    )
    project_update.add_argument(
        "--tag",
        dest="tags",
        action="append",
        metavar="NAME",
        help="Add a tag (repeatable)",
    )
    project_update.add_argument(
        "--remove-tag",
        dest="remove_tags",
        action="append",
        metavar="NAME",
        help="Remove a tag (repeatable)",
    )

    # search
    search_parser = subparsers.add_parser("search", help="Search projects by metadata")
    search_parser.add_argument("query", nargs="?", help="Free-text search query")
    search_parser.add_argument("--domain", help="Filter by domain")
    search_parser.add_argument(
        "--status", help="Filter by status (active/paused/done/archived)"
    )
    search_parser.add_argument(
        "--tag",
        dest="tags",
        action="append",
        metavar="NAME",
        help="Filter by tag (repeatable, all must match)",
    )
    search_parser.add_argument(
        "--from",
        dest="date_from",
        metavar="DATE",
        help="Only projects created on or after this ISO date",
    )
    search_parser.add_argument(
        "--to",
        dest="date_to",
        metavar="DATE",
        help="Only projects created on or before this ISO date",
    )

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
    elif args.command == "info":
        _handle_info(args)
    elif args.command == "project":
        _handle_project(args, project_parser)
    elif args.command == "search":
        _handle_search(args)
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

    col_slug = max(len(p.slug) for p in projects)
    col_status = max(len(p.status) for p in projects)
    col_slug = max(col_slug, 4)
    col_status = max(col_status, 6)

    header = f"{'SLUG':<{col_slug}}  {'STATUS':<{col_status}}  TITLE"
    print(header)
    print("-" * len(header))
    for p in projects:
        print(f"{p.slug:<{col_slug}}  {p.status:<{col_status}}  {p.title}")


def _handle_search(args: argparse.Namespace) -> None:
    """Search projects by text and/or structured filters."""
    from data_project_manager.core.search import search_projects

    if not any(
        [args.query, args.domain, args.status, args.tags, args.date_from, args.date_to]
    ):
        print("Error: provide a search query or at least one filter.", file=sys.stderr)
        sys.exit(1)

    results = search_projects(
        args.query,
        domain=args.domain,
        status=args.status,
        tags=args.tags,
        date_from=args.date_from,
        date_to=args.date_to,
    )

    if not results:
        print("No projects found.")
        return

    col_slug = max(len(r.slug) for r in results)
    col_status = max(len(r.status) for r in results)
    col_slug = max(col_slug, 4)
    col_status = max(col_status, 6)

    print(f"Found {len(results)} project(s):\n")
    header = f"{'SLUG':<{col_slug}}  {'STATUS':<{col_status}}  TITLE"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r.slug:<{col_slug}}  {r.status:<{col_status}}  {r.title}")


def _handle_info(args: argparse.Namespace) -> None:
    """Display all metadata for a project."""
    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.changelog import ChangeLogRepository
    from data_project_manager.db.repositories.person import ProjectPersonRepository
    from data_project_manager.db.repositories.project import ProjectRepository
    from data_project_manager.db.repositories.tag import ProjectTagRepository

    conn = get_connection()
    try:
        project = ProjectRepository(conn).get_by_slug(args.slug)
        if project is None:
            print(f"Error: project '{args.slug}' not found.", file=sys.stderr)
            sys.exit(1)

        pid = project.id
        tags = ProjectTagRepository(conn).list_for_project(pid)
        people = ProjectPersonRepository(conn).list_for_project(pid)
        log = ChangeLogRepository(conn).list_for_entity("project", pid)

        width = 60
        pad = max(0, width - 5 - len(project.title))
        print(f"\n{'─' * 3} {project.title} {'─' * pad}")

        info_fields = [
            ("Slug", project.slug),
            ("Status", project.status),
            ("Domain", project.domain or ""),
            ("Description", project.description or ""),
            ("Template", project.template_used or ""),
            ("Git", "yes" if project.has_git_repo else "no"),
            ("Path", project.relative_path or ""),
            ("Request date", project.request_date or ""),
            ("Expected start", project.expected_start or ""),
            ("Expected end", project.expected_end or ""),
            ("Realized start", project.realized_start or ""),
            ("Realized end", project.realized_end or ""),
            ("Est. hours", str(project.estimated_hours or "")),
        ]
        for label, value in info_fields:
            if value:
                print(f"  {label:<16} {value}")

        if tags:
            print(f"\n  Tags: {', '.join(t.name for t in tags)}")

        if people:
            print("\n  People:")
            for p in people:
                full = f"{p.first_name} {p.last_name}"
                print(f"    {full:<24} {p.role}")

        if log:
            print("\n  Change log (last 5):")
            for entry in log[-5:]:
                ts = entry.changed_at[:19]
                print(
                    f"    {ts}  {entry.field_name:<16}"
                    f"  {entry.old_value} → {entry.new_value}"
                )
        print()
    finally:
        conn.close()


def _handle_project(
    args: argparse.Namespace,
    project_parser: argparse.ArgumentParser,
) -> None:
    """Dispatch project sub-commands."""
    if args.project_command is None:
        project_parser.print_help()
        return
    if args.project_command == "update":
        _handle_project_update(args)


def _handle_project_update(args: argparse.Namespace) -> None:
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

        project = repo.get_by_slug(args.slug)
        if project is None:
            print(f"Error: project '{args.slug}' not found.", file=sys.stderr)
            sys.exit(1)

        pid = project.id

        # Collect scalar field updates
        updates: dict = {}
        if args.status is not None:
            valid = {"active", "paused", "done", "archived"}
            if args.status not in valid:
                print(
                    f"Error: invalid status '{args.status}'. "
                    f"Must be one of {sorted(valid)}.",
                    file=sys.stderr,
                )
                sys.exit(1)
            updates["status"] = args.status
        if args.domain is not None:
            updates["domain"] = args.domain
        if args.description is not None:
            updates["description"] = args.description
        if args.external_url is not None:
            updates["external_url"] = args.external_url

        if updates:
            repo.update(pid, **updates)

        # Tag operations
        tag_repo = TagRepository(conn)
        pt_repo = ProjectTagRepository(conn)
        for name in args.tags or []:
            tag = tag_repo.create(name=name)
            pt_repo.add(project_id=pid, tag_id=tag.id)
        for name in args.remove_tags or []:
            tag = tag_repo.get_by_name(name)
            if tag:
                pt_repo.remove(project_id=pid, tag_id=tag.id)

        if not updates and not args.tags and not args.remove_tags:
            print("Nothing to update.")
            return

        # Print summary
        print(f"Updated '{args.slug}':")
        for key, new_val in updates.items():
            print(f"  {key}: {getattr(project, key)} → {new_val}")
        for name in args.tags or []:
            print(f"  tag added: {name}")
        for name in args.remove_tags or []:
            print(f"  tag removed: {name}")
        print()
    finally:
        conn.close()


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
