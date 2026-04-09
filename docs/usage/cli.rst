CLI Reference
=============

All commands are available via ``datapm`` (Typer) or
``python -m data_project_manager`` (argparse fallback).  The examples
below use ``datapm``.

.. contents:: Commands
   :local:
   :depth: 1


datapm new
----------

Create a new project interactively or as a one-liner.

.. code-block:: text

   datapm new [NAME] [OPTIONS]

**Options**:

.. list-table::
   :widths: 30 70

   * - ``--domain TEXT``
     - Subject area (e.g. ``marketing``, ``healthcare``)
   * - ``--description TEXT``
     - Free-text description
   * - ``--type TEXT``
     - Archetype: ``minimal``, ``analysis``, ``modeling``,
       ``reporting``, ``research``, ``full``
   * - ``--folder KEY``
     - Explicit folder key (repeatable, bypasses archetype)
   * - ``--add KEY``
     - Add folder to archetype defaults
   * - ``--remove KEY``
     - Remove folder from archetype defaults
   * - ``--git / --no-git``
     - Initialise ``git`` in ``src/``
   * - ``--adhoc``
     - Mark as an ad-hoc request

**Examples**:

.. code-block:: bash

   # Interactive — prompts for all fields
   datapm new

   # One-liner with archetype
   datapm new "Q1 Sales Report" --domain finance --type reporting --no-git

   # Custom folder set
   datapm new "ML Experiment" --folder data --folder src --folder notebooks --git

   # Archetype with adjustments
   datapm new "Risk Model" --type modeling --add notebooks --remove models


datapm list
-----------

List all projects in a table.

.. code-block:: text

   datapm list [OPTIONS]

**Options**:

.. list-table::
   :widths: 30 70

   * - ``--status TEXT``
     - Filter by status (``active``, ``paused``, ``done``, ``archived``)
   * - ``--domain TEXT``
     - Filter by domain

**Examples**:

.. code-block:: bash

   datapm list
   datapm list --status active
   datapm list --status done --domain healthcare


datapm info
-----------

Show full metadata for a single project.

.. code-block:: text

   datapm info SLUG

Displays: slug, status, domain, description, template, path, dates,
tags, people, and the last 5 changelog entries.

**Example**:

.. code-block:: bash

   datapm info 2026-04-09-churn-analysis


datapm search
-------------

Search projects by free text and/or structured filters.

.. code-block:: text

   datapm search [QUERY] [OPTIONS]

**Options**:

.. list-table::
   :widths: 30 70

   * - ``--domain TEXT``
     - Filter by domain
   * - ``--status TEXT``
     - Filter by status
   * - ``--tag NAME``
     - Filter by tag (repeatable)
   * - ``--from DATE``
     - Projects created on or after this ISO date
   * - ``--to DATE``
     - Projects created on or before this ISO date

At least one of ``QUERY`` or a filter option is required.

**Examples**:

.. code-block:: bash

   # Free-text search
   datapm search "churn"

   # Structured filters only
   datapm search --domain healthcare --status active

   # Combined
   datapm search "model" --tag machine-learning --from 2026-01-01


datapm export
-------------

Export project metadata as structured JSON.

.. code-block:: text

   datapm export [SLUG] [OPTIONS]

**Options**:

==================== =================================
``--all``            Export all projects (index)
``--output FILE``    Write to file instead of stdout
``--compact``        Minified JSON (no indentation)
==================== =================================

When ``SLUG`` is omitted, exports the full index (same as ``--all``).

**Examples**:

.. code-block:: bash

   # Single project to stdout (syntax-highlighted with Typer)
   datapm export 2026-04-09-churn-analysis

   # All projects to file
   datapm export --all --output projects.json

   # Compact for piping
   datapm export 2026-04-09-churn-analysis --compact | jq .tags


datapm project update
---------------------

Update mutable fields on an existing project.

.. code-block:: text

   datapm project update SLUG [OPTIONS]

**Options**:

======================== ==========================================
``--status TEXT``        New status (``active``/``paused``/``done``/``archived``)
``--domain TEXT``        Subject area
``--description TEXT``   Free-text description
``--external-url TEXT``  DevOps/Trello link
``--tag NAME``           Add a tag (repeatable)
``--remove-tag NAME``    Remove a tag (repeatable)
======================== ==========================================

All changes are recorded in the changelog automatically.

**Examples**:

.. code-block:: bash

   datapm project update 2026-04-09-churn-analysis --status done
   datapm project update 2026-04-09-churn-analysis --tag machine-learning --tag python
   datapm project update 2026-04-09-churn-analysis --remove-tag draft


datapm config init
------------------

Create ``~/.datapm/config.json`` with default values.

.. code-block:: text

   datapm config init [--force]

Pass ``--force`` to overwrite an existing config file.
