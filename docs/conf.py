"""Sphinx configuration for Data Project Manager documentation."""

import importlib.metadata

project = "Data Project Manager"
author = "wiskas1000"
release = importlib.metadata.version("data-project-manager")
version = ".".join(release.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

# Napoleon settings (Google-style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = False

# Autodoc settings
autodoc_member_order = "bysource"
autodoc_typehints = "description"

# Intersphinx links to Python stdlib docs
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# HTML theme
html_theme = "alabaster"
html_theme_options = {
    "description": "A project launcher and metadata database for analytical work.",
    "github_user": "wiskas1000",
    "github_repo": "data-project-manager",
}
