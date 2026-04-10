FAQ
===

Where is the database?
----------------------

By default at ``~/.datapm/projects.db``.  Override it by adding a
``db_path`` key under ``general`` in ``~/.datapm/config.json``:

.. code-block:: json

   {
     "general": {
       "db_path": "/path/to/shared/projects.db"
     }
   }

Can I use this on a shared/network drive?
------------------------------------------

Yes.  Configure the ``roots`` in config to point to a shared drive
path.  The database itself should be on a local filesystem (SQLite
does not support concurrent access over network shares reliably).

What happens if Typer is not installed?
---------------------------------------

The CLI falls back to stdlib ``argparse`` automatically.  Every command
works identically — only the visual formatting differs (no colours, no
Rich tables).  The ``core/`` and ``db/`` layers have **zero** external
dependencies.

How do I register files from a data pipeline?
----------------------------------------------

Import the repository classes directly in your Python script:

.. code-block:: python

   from data_project_manager.db.connection import get_connection
   from data_project_manager.db.repositories.data_file import DataFileRepository

   conn = get_connection()
   repo = DataFileRepository(conn)
   repo.create(
       project_id="...",
       file_path="data/raw/customers.csv",
       sensitivity="client_confidential",
   )
   conn.close()

See :doc:`library` for a full pipeline example.

How does search work?
---------------------

``datapm search`` uses SQLite **FTS5** (Full-Text Search 5).  An FTS
virtual table indexes project titles, descriptions, domains, and slugs.
Triggers keep the index in sync when projects are created, updated, or
deleted.  Prefix matching is supported (e.g. ``churn*``).

Can I export for use with an LLM?
----------------------------------

Yes.  ``datapm export --all --compact`` produces a single JSON document
with all project metadata — ideal for feeding into an LLM context
window.  The structure includes projects with their tags, people, data
files, deliverables, queries, and questions.

How do I change a project's status?
-------------------------------------

.. code-block:: bash

   datapm project update 2026-04-09-churn-analysis --status done

Valid statuses: ``active``, ``paused``, ``done``, ``archived``.  The
change is recorded in the project's changelog automatically.

Why does ``datapm new`` say "Project folder already exists"?
-------------------------------------------------------------

The target folder (e.g. ``2026-04-10_Churn-Analysis/``) already exists
on disk — typically from a previous ``datapm new`` with the same name on
the same date.  The command checks for this **before** creating a
database record, so no orphan data is left behind.  Choose a different
project name or delete/rename the existing folder.

What is ``project.json``?
--------------------------

A one-directional metadata snapshot exported from the database into
the project folder.  The **database is the source of truth** —
``project.json`` is created during ``datapm new`` and refreshed by
``datapm export <slug>``.  Editing ``project.json`` by hand has no
effect on the database.

How do I back up the database?
-------------------------------

Copy ``~/.datapm/projects.db`` (or the path from your config).  SQLite
databases are single files — any file-level backup tool works.  For a
consistent snapshot while the database may be in use:

.. code-block:: bash

   sqlite3 ~/.datapm/projects.db ".backup /path/to/backup.db"
