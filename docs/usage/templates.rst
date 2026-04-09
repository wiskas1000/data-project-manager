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
     - Folders
     - Use case
   * - minimal
     - (base folders only)
     - Quick ad-hoc requests
   * - analysis
     - data, src
     - Standard data analysis
   * - modeling
     - data, src, models
     - ML / statistical modeling
   * - reporting
     - data, src, resultaten
     - Reports and dashboards
   * - research
     - data, src, literatuur
     - Academic / research projects
   * - full
     - data, src, models, resultaten, literatuur, notebooks
     - Everything

Every project always gets the **base folders**: ``communicatie/`` and
``documenten/``.

Selecting an archetype
----------------------

**Interactive** — ``datapm new`` shows a numbered picker:

.. code-block:: text

   Project type:
     ❯ Analysis     Standard data analysis
       Minimal      Quick ad-hoc requests
       Modeling     ML / statistical modeling
       ...
   Select [1-6]:

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
