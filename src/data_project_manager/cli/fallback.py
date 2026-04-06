"""Fallback CLI using stdlib argparse (zero dependencies)."""

import argparse


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

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
    elif args.command == "new":
        print(f"Creating project: {args.name} (domain={args.domain})")
    elif args.command == "search":
        print(f"Searching for: {args.query}")


if __name__ == "__main__":
    main()
