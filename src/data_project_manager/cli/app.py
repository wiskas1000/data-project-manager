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

project_app = typer.Typer(help="Manage project metadata.")
app.add_typer(project_app, name="project")

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
            p.slug,
            _status_text(p.status),
            p.domain or "",
            p.title,
        )

    _console.print(table)


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


@app.command()
def info(
    slug: Annotated[str, typer.Argument(help="Project slug")],
) -> None:
    """Show all metadata for a project."""
    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.changelog import ChangeLogRepository
    from data_project_manager.db.repositories.person import ProjectPersonRepository
    from data_project_manager.db.repositories.project import ProjectRepository
    from data_project_manager.db.repositories.tag import ProjectTagRepository

    conn = get_connection()
    try:
        project = ProjectRepository(conn).get_by_slug(slug)
        if project is None:
            _err_console.print(f"[bold red]Error:[/] project '{slug}' not found.")
            raise typer.Exit(1)

        pid = project.id
        tags = ProjectTagRepository(conn).list_for_project(pid)
        people = ProjectPersonRepository(conn).list_for_project(pid)
        log = ChangeLogRepository(conn).list_for_entity("project", pid)

        # Core fields table
        table = Table(box=None, pad_edge=False, show_header=False)
        table.add_column(style="dim", no_wrap=True)
        table.add_column()

        field_rows = [
            ("Slug", project.slug),
            ("Status", _status_text(project.status)),
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
        for label, value in field_rows:
            if value and str(value):
                table.add_row(label, value)

        _console.print(
            Panel(
                table,
                title=f"[bold]{project.title}[/]",
                expand=False,
            )
        )

        # Tags
        if tags:
            tag_names = ", ".join(f"[cyan]{t.name}[/]" for t in tags)
            _console.print(f"[dim]Tags:[/] {tag_names}")

        # People
        if people:
            _console.print("[dim]People:[/]")
            for p in people:
                full = f"{p.first_name} {p.last_name}"
                _console.print(f"  {full:<24} [dim]{p.role}[/]")

        # Change log
        if log:
            _console.print("[dim]Change log (last 5):[/]")
            for entry in log[-5:]:
                ts = entry.changed_at[:19]
                field = entry.field_name
                old = entry.old_value or "[dim]—[/]"
                new = entry.new_value or "[dim]—[/]"
                _console.print(f"  [dim]{ts}[/]  {field:<16}  {old} → {new}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# project update
# ---------------------------------------------------------------------------


@project_app.command("update")
def project_update(
    slug: Annotated[str, typer.Argument(help="Project slug")],
    status: Annotated[
        str | None, typer.Option(help="New status (active/paused/done/archived)")
    ] = None,
    domain: Annotated[str | None, typer.Option(help="Subject area")] = None,
    description: Annotated[
        str | None, typer.Option(help="Free-text description")
    ] = None,
    external_url: Annotated[
        str | None, typer.Option("--external-url", help="DevOps/Trello URL")
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Add a tag (repeatable)"),
    ] = None,
    remove_tags: Annotated[
        list[str] | None,
        typer.Option("--remove-tag", help="Remove a tag (repeatable)"),
    ] = None,
) -> None:
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

        project = repo.get_by_slug(slug)
        if project is None:
            _err_console.print(f"[bold red]Error:[/] project '{slug}' not found.")
            raise typer.Exit(1)

        pid = project.id

        # Validate and collect scalar updates
        updates: dict = {}
        if status is not None:
            valid = {"active", "paused", "done", "archived"}
            if status not in valid:
                _err_console.print(
                    f"[bold red]Error:[/] invalid status '{status}'. "
                    f"Must be one of {sorted(valid)}."
                )
                raise typer.Exit(1)
            updates["status"] = status
        if domain is not None:
            updates["domain"] = domain
        if description is not None:
            updates["description"] = description
        if external_url is not None:
            updates["external_url"] = external_url

        if updates:
            repo.update(pid, **updates)

        # Tag operations
        tag_repo = TagRepository(conn)
        pt_repo = ProjectTagRepository(conn)
        for name in tags or []:
            tag = tag_repo.create(name=name)
            pt_repo.add(project_id=pid, tag_id=tag.id)
        for name in remove_tags or []:
            tag = tag_repo.get_by_name(name)
            if tag:
                pt_repo.remove(project_id=pid, tag_id=tag.id)

        if not updates and not tags and not remove_tags:
            _console.print("[dim]Nothing to update.[/]")
            return

        _console.print(f"[bold green]✓[/] Updated [cyan]{slug}[/]")
        for key, new_val in updates.items():
            old_val = getattr(project, key)
            _console.print(f"  [dim]{key}:[/] {old_val} → [bold]{new_val}[/]")
        for name in tags or []:
            _console.print(f"  [dim]tag added:[/] [cyan]{name}[/]")
        for name in remove_tags or []:
            _console.print(f"  [dim]tag removed:[/] [cyan]{name}[/]")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@app.command()
def search(
    query: Annotated[str | None, typer.Argument(help="Free-text search query")] = None,
    domain: Annotated[str | None, typer.Option(help="Filter by domain")] = None,
    status: Annotated[
        str | None,
        typer.Option(help="Filter by status (active/paused/done/archived)"),
    ] = None,
    tags: Annotated[
        list[str] | None,
        typer.Option("--tag", help="Filter by tag (repeatable)"),
    ] = None,
    date_from: Annotated[
        str | None,
        typer.Option("--from", help="Projects created on or after this ISO date"),
    ] = None,
    date_to: Annotated[
        str | None,
        typer.Option("--to", help="Projects created on or before this ISO date"),
    ] = None,
) -> None:
    """Search projects by text and/or structured filters."""
    from data_project_manager.core.search import search_projects

    if not any([query, domain, status, tags, date_from, date_to]):
        _err_console.print(
            "[bold red]Error:[/] provide a search query or at least one filter."
        )
        raise typer.Exit(1)

    results = search_projects(
        query,
        domain=domain,
        status=status,
        tags=tags,
        date_from=date_from,
        date_to=date_to,
    )

    if not results:
        _console.print("[dim]No projects found.[/]")
        return

    _console.print(f"Found [bold]{len(results)}[/] project(s):\n")
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
    table.add_column("Description", style="dim", max_width=40)

    for r in results:
        desc = (r.description or "")[:40]
        if r.description and len(r.description) > 40:
            desc = desc[:37] + "..."
        table.add_row(
            r.slug,
            _status_text(r.status),
            r.domain or "",
            r.title,
            desc,
        )

    _console.print(table)


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


@app.command()
def export(
    slug: Annotated[
        str | None, typer.Argument(help="Project slug (omit for full index)")
    ] = None,
    export_all: Annotated[
        bool, typer.Option("--all", help="Export all projects")
    ] = False,
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Write JSON to file instead of stdout"),
    ] = None,
    compact: Annotated[
        bool, typer.Option("--compact", help="Minified JSON (no indentation)")
    ] = False,
) -> None:
    """Export project metadata as structured JSON."""
    from data_project_manager.core.export import export_all_json, export_project_json

    pretty = not compact
    if export_all or slug is None:
        json_output = export_all_json(pretty=pretty)
    else:
        json_output = export_project_json(slug, pretty=pretty)
        if json_output is None:
            _err_console.print(f"[bold red]Error:[/] project '{slug}' not found.")
            raise typer.Exit(1)

    if output:
        from pathlib import Path

        Path(output).write_text(json_output + "\n", encoding="utf-8")
        _console.print(f"[bold green]✓[/] Exported to [cyan]{output}[/]")
    else:
        from rich.syntax import Syntax

        _console.print(Syntax(json_output, "json", theme="monokai"))


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


def _redraw(num_lines: int) -> None:
    """Move cursor up *num_lines* and clear to end of screen."""
    sys.stdout.write(f"\x1b[{num_lines}A\x1b[J")
    sys.stdout.flush()


def _prompt_archetype_rich(default_key: str = "analysis") -> str:
    """Show a Rich-formatted archetype picker."""
    from data_project_manager.core.templates import BUILT_IN_ARCHETYPES

    keys = list(BUILT_IN_ARCHETYPES)
    cursor = keys.index(default_key) if default_key in keys else 1

    # Fall back to number-based when not interactive.
    try:
        import termios as _termios  # noqa: F401

        interactive = sys.stdin.isatty()
    except ImportError:
        interactive = False

    if not interactive:
        return _prompt_archetype_numbered(keys, BUILT_IN_ARCHETYPES, cursor)

    # Number of printed lines: 1 header + len(keys) items.
    num_lines = 1 + len(keys)

    def render() -> None:
        _console.print("[bold]Project type[/]  [dim]↑↓ move · Enter select[/]")
        for i, key in enumerate(keys):
            arch = BUILT_IN_ARCHETYPES[key]
            is_cur = i == cursor
            if is_cur:
                marker = "[bold cyan]❯[/]"
                style = "bold"
            else:
                marker = " "
                style = ""
            padded = f"{arch.label:<12s}"
            label = f"[{style}]{padded}[/{style}]" if style else padded
            num = f"[dim]\\[{i + 1}][/dim]"
            _console.print(f"  {marker} {num} {label}  [dim]{arch.description}[/dim]")

    _console.print()
    render()
    while True:
        key = _read_key()
        if key == "up" and cursor > 0:
            cursor -= 1
        elif key == "down" and cursor < len(keys) - 1:
            cursor += 1
        elif key == "enter":
            _redraw(num_lines)
            render()
            break
        elif key.isdigit():
            n = int(key)
            if 1 <= n <= len(keys):
                cursor = n - 1
                _redraw(num_lines)
                render()
                break
            continue
        else:
            continue
        _redraw(num_lines)
        render()

    return keys[cursor]


def _prompt_archetype_numbered(
    keys: list[str],
    archetypes: dict,
    default_idx: int,
) -> str:
    """Number-based archetype picker for non-interactive terminals."""
    _console.print("\n[bold]Project type:[/]")
    for i, key in enumerate(keys):
        arch = archetypes[key]
        if i == default_idx:
            marker = "[bold cyan]❯[/]"
            style = "bold"
        else:
            marker = " "
            style = ""
        padded = f"{arch.label:<12s}"
        label = f"[{style}]{padded}[/{style}]" if style else padded
        num = f"[dim][{i + 1}][/dim]"
        _console.print(f"  {marker} {num} {label}  [dim]{arch.description}[/dim]")

    raw = typer.prompt(f"Select [1-{len(keys)}]", default=str(default_idx + 1))
    try:
        choice = int(raw)
        if 1 <= choice <= len(keys):
            return keys[choice - 1]
    except ValueError:
        pass
    return keys[default_idx]


def _read_key() -> str:
    """Read a single keypress via raw terminal I/O.

    Returns 'up', 'down', 'space', 'enter', 'escape', 'q',
    a digit character, or ''.
    """
    import os
    import select

    try:
        import termios
        import tty
    except ImportError:
        return ""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = os.read(fd, 1)
        if ch == b"\x1b":
            # Arrow keys send \x1b[A / \x1b[B — peek for more bytes.
            ready, _, _ = select.select([fd], [], [], 0.05)
            if ready and os.read(fd, 1) == b"[":
                arrow = os.read(fd, 1)
                return {b"A": "up", b"B": "down"}.get(arrow, "")
            return "escape"
        if ch == b" ":
            return "space"
        if ch in (b"\r", b"\n"):
            return "enter"
        if ch == b"\x03":
            raise KeyboardInterrupt
        if ch == b"q":
            return "q"
        decoded = ch.decode("ascii", errors="ignore")
        if decoded.isdigit():
            return decoded
        return ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _read_key_timeout(timeout: float) -> str | None:
    """Read a keypress with timeout. Returns None on timeout."""
    import os
    import select

    try:
        import termios
        import tty
    except ImportError:
        return None
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ready, _, _ = select.select([fd], [], [], timeout)
        if not ready:
            return None
        ch = os.read(fd, 1)
        if ch in (b"\r", b"\n"):
            return "enter"
        if ch == b"\x1b":
            return "escape"
        if ch == b"q":
            return "q"
        if ch == b"\x03":
            raise KeyboardInterrupt
        return ch.decode("ascii", errors="ignore")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _prompt_folder_toggles_rich(current: list[str]) -> list[str]:
    """Interactive folder picker with arrow keys, Space, and Enter."""
    from data_project_manager.core.templates import (
        OPTIONAL_FOLDERS,
        SRC_TOGGLES,
        resolve_folders,
    )

    display_order = [f for f in OPTIONAL_FOLDERS if f not in SRC_TOGGLES] + SRC_TOGGLES
    selected = set(current)
    cursor = 0

    # Fall back to number-based input when stdin is not a real terminal.
    try:
        import termios as _termios  # noqa: F401

        interactive = sys.stdin.isatty()
    except ImportError:
        interactive = False

    if not interactive:
        return _prompt_folder_toggles_numbered(display_order, selected)

    num_lines = 1 + len(display_order)

    def render() -> None:
        _console.print(
            "[bold]Folders[/]  [dim]↑↓ move · Space toggle · Enter confirm[/]"
        )
        for i, key in enumerate(display_order):
            is_cur = i == cursor
            indent = "    " if key in SRC_TOGGLES else ""
            label = f"src/{key}/" if key in SRC_TOGGLES else f"{key}/"
            marker = "[bold cyan]❯[/]" if is_cur else " "
            check = "[green]✓[/]" if key in selected else "[dim]○[/]"
            style = "bold" if is_cur else ""
            name = f"{indent}{label}"
            styled = f"[{style}]{name}[/{style}]" if style else name
            _console.print(f"  {marker} {check} {styled}")

    _console.print()
    render()
    while True:
        key = _read_key()
        if key == "up" and cursor > 0:
            cursor -= 1
        elif key == "down" and cursor < len(display_order) - 1:
            cursor += 1
        elif key == "space":
            selected.symmetric_difference_update({display_order[cursor]})
        elif key == "enter":
            _redraw(num_lines)
            render()
            break
        else:
            continue
        _redraw(num_lines)
        render()

    result = resolve_folders(sorted(selected))

    # Confirmation countdown — wait 3 s, Enter to skip, Esc/q to abort.
    folder_str = ", ".join(f"{f}/" for f in result) if result else "(none)"
    _console.print(f"[dim]Selected:[/] {folder_str}")
    for remaining in range(3, 0, -1):
        _console.print(
            f"[dim]Confirming in {remaining}s… (Enter to skip, Esc to abort)[/]",
            end="\r",
        )
        pressed = _read_key_timeout(1.0)
        if pressed == "enter":
            _console.print()
            break
        if pressed in ("escape", "q"):
            _console.print("\n[yellow]Aborted.[/]")
            raise typer.Abort()
    else:
        _console.print()

    return result


def _prompt_folder_toggles_numbered(
    display_order: list[str], selected: set[str]
) -> list[str]:
    """Number-based folder toggle fallback for non-interactive terminals."""
    from data_project_manager.core.templates import SRC_TOGGLES, resolve_folders

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
                selected.symmetric_difference_update({key})
        except ValueError:
            continue

    return resolve_folders(sorted(selected))


if __name__ == "__main__":
    app()
