Using as a Library
==================

The repository layer is a first-class Python API.  Any data pipeline,
scanner, or dashboard can import it directly — no CLI required.

All repositories return **frozen dataclasses** with typed attributes
(e.g. ``project.id``, ``project.slug``), providing IDE autocompletion
and eliminating ``KeyError`` risks from dict access.

Getting a connection
--------------------

.. code-block:: python

    from data_project_manager.db.connection import get_connection

    conn = get_connection()                  # reads ~/.datapm/config.json
    conn = get_connection("/path/to/my.db")  # explicit path (scripts / tests)

The connection runs all pending migrations automatically, so calling code
never needs to manage the schema.

Full pipeline example
---------------------

The snippet below shows a data pipeline registering its outputs after a
successful run.

.. code-block:: python

    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.changelog import ChangeLogRepository
    from data_project_manager.db.repositories.data_file import (
        AggregationLevelRepository,
        DataFileRepository,
        EntityTypeRepository,
    )
    from data_project_manager.db.repositories.deliverable import DeliverableRepository
    from data_project_manager.db.repositories.person import (
        PersonRepository,
        ProjectPersonRepository,
    )
    from data_project_manager.db.repositories.project import ProjectRepository
    from data_project_manager.db.repositories.tag import (
        ProjectTagRepository,
        TagRepository,
    )

    conn = get_connection()

    # 1. Look up the project by slug
    project_repo = ProjectRepository(conn, changelog=ChangeLogRepository(conn))
    project = project_repo.get_by_slug("2026-01-15-churn-analysis")

    # 2. Register a person and link them to the project
    person_repo = PersonRepository(conn)
    person = person_repo.create(
        first_name="Ana",
        last_name="García",
        email="analyst@example.com",
        function_title="Senior Analyst",
        department="Analytics",
    )
    ProjectPersonRepository(conn).add(
        project_id=project.id,
        person_id=person.id,
        role="analyst",
    )

    # 3. Tag the project
    tag = TagRepository(conn).create(name="churn")
    ProjectTagRepository(conn).add(project.id, tag.id)

    # 4. Register an output file
    entity_type = EntityTypeRepository(conn).create(name="customers")
    agg_level = AggregationLevelRepository(conn).create(name="row")

    data_file_repo = DataFileRepository(conn)
    data_file = data_file_repo.create(
        project_id=project.id,
        file_path="data/processed/churn_scores_2026Q1.parquet",
        file_format="parquet",
        sensitivity="client_confidential",
    )
    data_file_repo.link_entity_type(data_file.id, entity_type.id)
    data_file_repo.link_aggregation_level(data_file.id, agg_level.id)

    # 5. Register a deliverable and mark it delivered
    deliverable_repo = DeliverableRepository(conn)
    deliverable = deliverable_repo.create(
        project_id=project.id,
        type="report",
        file_path="results/churn_report_Q1_2026.pdf",
        file_format="pdf",
    )
    deliverable_repo.mark_delivered(deliverable.id)

    conn.close()

Reading the audit trail
-----------------------

Every field changed via :meth:`~data_project_manager.db.repositories.project.ProjectRepository.update`
is recorded automatically when a :class:`~data_project_manager.db.repositories.changelog.ChangeLogRepository`
is injected:

.. code-block:: python

    from data_project_manager.db.connection import get_connection
    from data_project_manager.db.repositories.changelog import ChangeLogRepository
    from data_project_manager.db.repositories.project import ProjectRepository

    conn = get_connection()
    changelog = ChangeLogRepository(conn)
    repo = ProjectRepository(conn, changelog=changelog)

    project = repo.get_by_slug("2026-01-15-churn-analysis")
    repo.update(project.id, status="done")

    for entry in changelog.list_for_entity("project", project.id):
        print(entry.field_name, entry.old_value, "->", entry.new_value)

Available data models
---------------------

All repository return types are frozen dataclasses in
:mod:`data_project_manager.db.models`:

============================== ============================================
Model                          Key attributes
============================== ============================================
``Project``                    id, title, slug, status, domain, description
``ProjectRoot``                id, name, absolute_path, is_default
``Person``                     id, first_name, last_name, email, is_current
``Tag``                        id, name, category
``DataFile``                   id, project_id, file_path, sensitivity
``Deliverable``                id, project_id, type, file_path, delivered_at
``Query``                      id, query_path, language, sensitivity
``RequestQuestion``            id, question, answer
``ChangeLogEntry``             id, entity_type, field_name, old_value, new_value
``SearchResult``               slug, title, status, domain, description
============================== ============================================

Import them for type annotations:

.. code-block:: python

    from data_project_manager.db.models import Project, Person, Tag
