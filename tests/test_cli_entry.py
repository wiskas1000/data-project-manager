"""Tests for cli/__init__.py (two-tier entry point) and __main__.py."""

import importlib


class TestCLIInit:
    """Test the two-tier CLI dispatch in cli/__init__.py."""

    def test_main_with_typer_available(self, monkeypatch):
        """When Typer is available, main() calls cli.app.app()."""
        called = []

        def fake_app():
            called.append("typer")

        monkeypatch.setattr("data_project_manager.cli.app.app", fake_app)

        from data_project_manager.cli import main

        main()
        assert called == ["typer"]

    def test_main_without_typer_falls_back(self, monkeypatch):
        """When Typer is absent, main() calls cli.fallback.main()."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "typer":
                raise ImportError("no typer")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        called = []

        def fake_fallback_main():
            called.append("argparse")

        monkeypatch.setattr(
            "data_project_manager.cli.fallback.main", fake_fallback_main
        )

        # Force re-execution of the dispatch logic
        from data_project_manager.cli import main

        main()
        assert called == ["argparse"]


class TestMainModule:
    """Test __main__.py entry point."""

    def test_main_module_calls_main(self, monkeypatch):
        """python -m data_project_manager invokes cli.main()."""
        called = []

        def fake_main():
            called.append("main")

        # Patch before reload so the top-level call uses the fake
        import data_project_manager.cli as cli_mod

        monkeypatch.setattr(cli_mod, "main", fake_main)

        import data_project_manager.__main__ as mod

        called.clear()  # clear any prior calls from the initial import
        importlib.reload(mod)
        assert called == ["main"]
