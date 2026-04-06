"""Default configuration values for Data Project Manager."""

from pathlib import Path

#: Directory where datapm stores its config and database.
DATAPM_DIR = Path.home() / ".datapm"

#: Default path to the config file.
CONFIG_PATH = DATAPM_DIR / "config.json"

#: Default path to the SQLite database.
DB_PATH = DATAPM_DIR / "projects.db"

#: Skeleton written by ``config init`` when no config exists.
DEFAULT_CONFIG: dict = {
    "general": {
        "default_root": "work",
    },
    "roots": {
        "work": {
            "path": str(Path.home() / "projects" / "work"),
        },
    },
    "defaults": {
        "template": "minimal",
        "git_init": True,
        "sensitivity": "internal",
    },
    "preferences": {
        "folder_language": "nl",
    },
}
