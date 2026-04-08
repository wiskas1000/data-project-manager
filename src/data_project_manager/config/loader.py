"""Config loading and persistence for Data Project Manager.

The config file lives at ``~/.datapm/config.json``.  All functions use
:mod:`pathlib` so they work on Windows, macOS, and Linux without changes.
"""

import json
from pathlib import Path
from typing import Any

from data_project_manager.config.defaults import (
    CONFIG_PATH,
    DB_PATH,
    DEFAULT_CONFIG,
)


def get_config_path() -> Path:
    """Return the path to the config file.

    Returns:
        Absolute path to ``~/.datapm/config.json``.
    """
    return CONFIG_PATH


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load the config from disk, falling back to defaults if absent.

    Args:
        config_path: Override the default config location.  Useful in tests.

    Returns:
        Parsed config dict.  Missing top-level keys are filled with their
        default values so callers can always rely on the full structure.
    """
    path = config_path or CONFIG_PATH
    if not path.exists():
        return _deep_merge(DEFAULT_CONFIG, {})

    with path.open("r", encoding="utf-8") as fh:
        on_disk = json.load(fh)

    return _deep_merge(DEFAULT_CONFIG, on_disk)


def save_config(config: dict[str, Any], config_path: Path | None = None) -> None:
    """Write *config* to disk, creating the directory if needed.

    Args:
        config: Config dict to serialise.
        config_path: Override the default config location.  Useful in tests.
    """
    path = config_path or CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
        fh.write("\n")


def init_config(config_path: Path | None = None, *, force: bool = False) -> Path:
    """Create the config file and ``~/.datapm/`` directory if they don't exist.

    Args:
        config_path: Override the default config location.  Useful in tests.
        force: Overwrite an existing config file.

    Returns:
        Path to the (possibly newly created) config file.

    Raises:
        FileExistsError: If the file already exists and *force* is ``False``.
    """
    path = config_path or CONFIG_PATH
    if path.exists() and not force:
        raise FileExistsError(
            f"Config already exists at {path}. Use --force to overwrite."
        )
    save_config(DEFAULT_CONFIG, path)
    return path


def get_db_path(config_path: Path | None = None) -> Path:
    """Return the database path defined in the config (or the default).

    Reads ``general.db_path`` if present; otherwise falls back to
    ``~/.datapm/projects.db``.

    Args:
        config_path: Override the default config location.  Useful in tests.

    Returns:
        Absolute path to the SQLite database file.
    """
    config = load_config(config_path)
    raw = config.get("general", {}).get("db_path")
    return Path(raw) if raw else DB_PATH


def get_default_root(config_path: Path | None = None) -> str | None:
    """Return the name of the default project root from config.

    Args:
        config_path: Override the default config location.  Useful in tests.

    Returns:
        Root name string, or ``None`` if not set.
    """
    config = load_config(config_path)
    return config.get("general", {}).get("default_root")


def get_root_path(root_name: str, config_path: Path | None = None) -> Path | None:
    """Return the filesystem path for a named root.

    Args:
        root_name: Key in the ``roots`` section of the config.
        config_path: Override the default config location.  Useful in tests.

    Returns:
        :class:`~pathlib.Path` for the root, or ``None`` if the root is not
        defined in the config.
    """
    config = load_config(config_path)
    roots = config.get("roots", {})
    entry = roots.get(root_name)
    return Path(entry["path"]) if entry and "path" in entry else None


def get_default_template(config_path: Path | None = None) -> str:
    """Return the default archetype/template key from config.

    Args:
        config_path: Override the default config location.  Useful in tests.

    Returns:
        Template key string (e.g. ``"analysis"``).  Falls back to
        ``"analysis"`` if not set.
    """
    config = load_config(config_path)
    return config.get("defaults", {}).get("template", "analysis")


def get_folder_language(config_path: Path | None = None) -> str:
    """Return the folder language preference from config.

    Args:
        config_path: Override the default config location.  Useful in tests.

    Returns:
        ``"nl"`` or ``"en"``.  Falls back to ``"nl"`` if not set.
    """
    config = load_config(config_path)
    return config.get("preferences", {}).get("folder_language", "nl")


def get_custom_templates(
    config_path: Path | None = None,
) -> dict[str, dict]:
    """Return custom templates defined in config.

    Args:
        config_path: Override the default config location.  Useful in tests.

    Returns:
        Dict of template name → ``{"description": ..., "folders": [...]}``.
    """
    config = load_config(config_path)
    return config.get("templates", {})


def get_git_init_default(config_path: Path | None = None) -> bool | None:
    """Return the ``defaults.git_init`` value from config.

    Args:
        config_path: Override the default config location.  Useful in tests.

    Returns:
        ``True``/``False`` if explicitly set, ``None`` if absent (meaning
        the user should be prompted).
    """
    config = load_config(config_path)
    val = config.get("defaults", {}).get("git_init")
    if val is None:
        return None
    return bool(val)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _deep_merge(base: dict, override: dict) -> dict:
    """Return a new dict that is *base* deep-merged with *override*.

    Nested dicts are merged recursively; all other values from *override*
    take precedence over *base*.

    Args:
        base: Default values.
        override: Values that take precedence.

    Returns:
        Merged dict (neither input is mutated).
    """
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
