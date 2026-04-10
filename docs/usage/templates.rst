Templates & Folder Customisation
=================================

Projects are scaffolded from **archetypes** — predefined folder sets
tailored to common analytical workflows.  You can use them as-is,
tweak them with ``--add``/``--remove``, or define your own in config.

Built-in archetypes
-------------------

.. list-table::
   :header-rows: 1
   :widths: 15 55 30

   * - Key
     - Optional folders
     - Use case
   * - minimal
     - *(none — base folders only)*
     - Quick ad-hoc requests
   * - analysis
     - data, src, notebooks, resultaten
     - Standard data analysis
   * - modeling
     - data, src, notebooks, resultaten, literatuur
     - ML / statistical modeling
   * - reporting
     - data, src, queries, resultaten
     - Reports and dashboards
   * - research
     - data, src, notebooks, literatuur, resultaten
     - Academic / research projects
   * - full
     - all optional folders
     - Everything

Every project always gets the **base folders**: ``communicatie/`` and
``documenten/``.

Selecting an archetype
----------------------

**Interactive** — ``datapm new`` shows an arrow-key picker (Rich/Typer):

.. code-block:: text

   Project type  ↑↓ move · Enter select
       [1] Minimal       communicatie, documenten
     ❯ [2] Analysis      + data, src, notebooks, resultaten
       [3] Modeling      + data, src, notebooks, resultaten, literatuur
       [4] Reporting     + data, src, queries, resultaten
       [5] Research      + data, src, notebooks, literatuur, resultaten
       [6] Full          all folders

Use arrow keys to navigate and Enter to select, or type a number for
quick selection.  In the argparse fallback the picker uses numbered
input only.

**One-liner** — use ``--type``:

.. code-block:: bash

   datapm new "My Project" --type modeling

Adjusting folders
-----------------

Add or remove folders from an archetype without switching to a
different one:

.. code-block:: bash

   # Start from "analysis", add notebooks
   datapm new "Experiment" --type analysis --add notebooks

   # Start from "full", remove models
   datapm new "Report" --type full --remove models

Explicit folder list
--------------------

Bypass archetypes entirely with ``--folder``:

.. code-block:: bash

   datapm new "Custom" --folder data --folder src --folder notebooks

Folder language
---------------

Folder names default to **Dutch** (``nl``): ``communicatie/``,
``documenten/``, ``resultaten/``, ``literatuur/``.

Set ``preferences.folder_language`` to ``"en"`` in
``~/.datapm/config.json`` to switch to English names:
``communications/``, ``documents/``, ``results/``, ``literature/``.

.. code-block:: json

   {
     "preferences": {
       "folder_language": "en"
     }
   }

Default archetype
-----------------

Set ``defaults.template`` in config to change the default selection in
the interactive picker:

.. code-block:: json

   {
     "defaults": {
       "template": "full"
     }
   }

Custom templates (config)
-------------------------

Define your own archetypes in ``~/.datapm/config.json`` under the
``templates`` key:

.. code-block:: json

   {
     "templates": {
       "dashboard": {
         "description": "BI dashboard project",
         "folders": ["data", "src", "resultaten"]
       }
     }
   }

Custom templates appear alongside the built-in ones in the interactive
picker and can be selected with ``--type dashboard``.
