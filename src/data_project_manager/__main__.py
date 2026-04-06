#!/usr/bin/env python3
"""Entry point for `python -m data_project_manager`."""

try:
    from data_project_manager.cli.app import app

    app()
except ImportError:
    from data_project_manager.cli.fallback import main

    main()
