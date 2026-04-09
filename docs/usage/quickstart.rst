Quickstart
==========

This guide gets you from zero to your first tracked project in under
two minutes.

Installation
------------

**With uv (recommended)**:

.. code-block:: bash

   git clone https://github.com/wiskas1000/data-project-manager
   cd data-project-manager
   uv sync                     # core (zero runtime dependencies)
   uv sync --extra enhanced    # add Rich/Typer for interactive prompts

**With pip**:

.. code-block:: bash

   pip install -e .
   pip install -e ".[enhanced]"   # optional Rich output

Initialise configuration
------------------------

.. code-block:: bash

   datapm config init

This creates ``~/.datapm/config.json`` with a default project root
pointing to ``~/projects/work/``.  Edit the file to change the root
directory or add additional roots.

Create your first project
-------------------------

**Interactive mode** — Typer prompts for every field:

.. code-block:: bash

   datapm new

**One-liner** — skip the prompts:

.. code-block:: bash

   datapm new "Churn Analysis" --domain marketing --type analysis --no-git

Both commands create a dated folder (e.g.
``2026-04-09_Churn-Analysis/``) with standard subfolders, write a
``project.json`` metadata snapshot, and insert a record into the SQLite
database.

Explore your projects
---------------------

.. code-block:: bash

   # List all projects
   datapm list
   datapm list --status active --domain healthcare

   # Full metadata for one project
   datapm info 2026-04-09-churn-analysis

   # Search across all projects
   datapm search "churn"
   datapm search --domain marketing --status done

   # Export structured JSON
   datapm export 2026-04-09-churn-analysis
   datapm export --all

Zero-dependency mode
--------------------

If Typer is not installed the CLI falls back to stdlib ``argparse``
automatically.  All commands work identically:

.. code-block:: bash

   python -m data_project_manager new "My Project"
   python -m data_project_manager list
   python -m data_project_manager search "keyword"

Next steps
----------

- :doc:`cli` — full CLI command reference with examples
- :doc:`library` — using the Python API from data pipelines
- :doc:`templates` — customising archetypes and folder structures
