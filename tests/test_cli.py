"""Basic CLI smoke tests."""

from data_project_manager import __version__


def test_version():
    assert __version__ == "1.2.0"
