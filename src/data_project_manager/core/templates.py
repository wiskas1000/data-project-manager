"""Project archetypes and folder mappings for ``datapm new``.

This module is **stdlib-only**.  It defines the built-in archetypes,
folder inventories, and helper functions that translate archetype keys
into concrete directory lists.

See ``docs/FOLDER-SELECTION-DESIGN.md`` for the full design rationale.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Folder name translations
# ---------------------------------------------------------------------------

#: On-disk folder names keyed by language then canonical key.
FOLDER_NAMES: dict[str, dict[str, str]] = {
    "nl": {
        "communicatie": "communicatie",
        "documenten": "documenten",
        "archief": "archief",
        "data": "data",
        "src": "src",
        "literatuur": "literatuur",
        "resultaten": "resultaten",
    },
    "en": {
        "communicatie": "communication",
        "documenten": "documents",
        "archief": "archive",
        "data": "data",
        "src": "src",
        "literatuur": "literature",
        "resultaten": "results",
    },
}

#: On-disk subfolder names keyed by language then canonical key.
SUBFOLDER_NAMES: dict[str, dict[str, str]] = {
    "nl": {
        "raw": "raw",
        "processed": "processed",
        "metadata": "metadata",
        "queries": "queries",
        "notebooks": "notebooks",
        "export": "export",
        "figuren": "figuren",
    },
    "en": {
        "raw": "raw",
        "processed": "processed",
        "metadata": "metadata",
        "queries": "queries",
        "notebooks": "notebooks",
        "export": "export",
        "figuren": "figures",
    },
}

# ---------------------------------------------------------------------------
# Folder structure definitions
# ---------------------------------------------------------------------------

#: Auto-created children when the parent folder is selected (not toggleable).
SUBFOLDERS: dict[str, list[str]] = {
    "data": ["raw", "processed", "metadata"],
    "resultaten": ["export", "figuren"],
}

#: ``src/`` sub-items that ARE independently toggleable.
SRC_TOGGLES: list[str] = ["notebooks", "queries"]

#: Folders created for every project regardless of archetype.
BASE_FOLDERS: list[str] = ["communicatie", "documenten"]

#: Keys accepted in archetype definitions, CLI flags, and config templates.
OPTIONAL_FOLDERS: list[str] = [
    "data",
    "src",
    "notebooks",
    "queries",
    "literatuur",
    "resultaten",
]

# ---------------------------------------------------------------------------
# Archetype dataclass and built-in presets
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Archetype:
    """A project archetype defining default optional folders.

    Attributes:
        key: Machine-readable identifier (e.g. ``"analysis"``).
        label: Short human-readable label for the picker.
        description: One-line description shown alongside the label.
        folders: Subset of :data:`OPTIONAL_FOLDERS` enabled by default.
    """

    key: str
    label: str
    description: str
    folders: list[str] = field(default_factory=list)


#: Built-in archetypes shipped with ``datapm``.
BUILT_IN_ARCHETYPES: dict[str, Archetype] = {
    "minimal": Archetype(
        key="minimal",
        label="Minimal",
        description="communicatie, documenten",
        folders=[],
    ),
    "analysis": Archetype(
        key="analysis",
        label="Analysis",
        description="+ data, src, notebooks, resultaten",
        folders=["data", "src", "notebooks", "resultaten"],
    ),
    "modeling": Archetype(
        key="modeling",
        label="Modeling",
        description="+ data, src, notebooks, resultaten, literatuur",
        folders=["data", "src", "notebooks", "literatuur", "resultaten"],
    ),
    "reporting": Archetype(
        key="reporting",
        label="Reporting",
        description="+ data, src, queries, resultaten",
        folders=["data", "src", "queries", "resultaten"],
    ),
    "research": Archetype(
        key="research",
        label="Research",
        description="+ data, src, notebooks, literatuur, resultaten",
        folders=["data", "src", "notebooks", "literatuur", "resultaten"],
    ),
    "full": Archetype(
        key="full",
        label="Full",
        description="all folders",
        folders=list(OPTIONAL_FOLDERS),
    ),
}


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------


def resolve_folders(
    selected: list[str],
    *,
    add: list[str] | None = None,
    remove: list[str] | None = None,
) -> list[str]:
    """Apply toggle overrides and enforce dependency constraints.

    Selecting ``notebooks`` or ``queries`` implicitly enables ``src``.
    Removing ``src`` also removes ``notebooks`` and ``queries``.

    Args:
        selected: Initial folder keys (from an archetype or explicit list).
        add: Additional folder keys to enable.
        remove: Folder keys to disable.

    Returns:
        De-duplicated, dependency-resolved list of folder keys.
    """
    result = set(selected)
    for key in add or []:
        result.add(key)

    removed = set(remove or [])
    for key in removed:
        result.discard(key)

    # If src was explicitly removed, also remove its children
    if "src" in removed:
        result.discard("notebooks")
        result.discard("queries")
    else:
        # notebooks/queries imply src
        if result & {"notebooks", "queries"}:
            result.add("src")

    return sorted(result)


def get_archetype(key: str) -> Archetype:
    """Look up a built-in archetype by key.

    Args:
        key: Archetype identifier (e.g. ``"analysis"``).

    Returns:
        The matching :class:`Archetype`.

    Raises:
        ValueError: If *key* is not a recognised archetype.
    """
    if key not in BUILT_IN_ARCHETYPES:
        raise ValueError(
            f"Unknown archetype {key!r}. Valid: {sorted(BUILT_IN_ARCHETYPES)}"
        )
    return BUILT_IN_ARCHETYPES[key]


def folder_display_name(key: str, language: str = "nl") -> str:
    """Return the on-disk name for a folder key in the given language.

    Args:
        key: Canonical folder key (e.g. ``"literatuur"``).
        language: ``"nl"`` or ``"en"``.

    Returns:
        Translated folder name.
    """
    names = FOLDER_NAMES.get(language, FOLDER_NAMES["nl"])
    return names.get(key, key)


def subfolder_display_name(key: str, language: str = "nl") -> str:
    """Return the on-disk name for a subfolder key in the given language.

    Args:
        key: Canonical subfolder key (e.g. ``"figuren"``).
        language: ``"nl"`` or ``"en"``.

    Returns:
        Translated subfolder name.
    """
    names = SUBFOLDER_NAMES.get(language, SUBFOLDER_NAMES["nl"])
    return names.get(key, key)
