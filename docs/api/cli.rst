CLI
===

The CLI has two implementations: an argparse fallback (zero dependencies)
and an enhanced Typer + Rich version (optional).  The entry point
auto-detects which is available.

Entry Point
-----------

.. automodule:: data_project_manager.cli
   :members:

Argparse Fallback
-----------------

.. automodule:: data_project_manager.cli.fallback
   :members:
   :private-members: _handle_new, _handle_list, _handle_search, _handle_export, _handle_info, _handle_project, _handle_project_update, _handle_config

Enhanced (Typer + Rich)
-----------------------

.. automodule:: data_project_manager.cli.app
   :members:
