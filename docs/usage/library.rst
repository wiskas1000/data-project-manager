Using as a Library
==================

The repository layer is a first-class Python API. Any data pipeline,
scanner, or dashboard can import it directly — no CLI required.

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
    person = person_repo.get_or_create(
        email="analyst@example.com",
        first_name="Ana",
        last_name="García",
        function_title="Senior Analyst",
        department="Analytics",
    )
    ProjectPersonRepository(conn).add(
        project_id=project["id"],
        person_id=person["id"],
        role="analyst",
    )

    # 3. Tag the project
    tag = TagRepository(conn).get_or_create("churn")
    ProjectTagRepository(conn).add(project["id"], tag["id"])

    # 4. Register an output file
    entity_type = EntityTypeRepository(conn).get_or_create("customers")
    agg_level = AggregationLevelRepository(conn).get_or_create("row")

    data_file_repo = DataFileRepository(conn)
    data_file = data_file_repo.create(
        project_id=project["id"],
        file_path="data/processed/churn_scores_2026Q1.parquet",
        sensitivity="client_confidential",
        description="Model scores per customer for Q1 2026",
    )
    data_file_repo.link_entity_type(data_file["id"], entity_type["id"])
    data_file_repo.link_aggregation_level(data_file["id"], agg_level["id"])

    # 5. Register a deliverable and mark it delivered
    deliverable_repo = DeliverableRepository(conn)
    deliverable = deliverable_repo.create(
        project_id=project["id"],
        title="Churn Score Report Q1 2026",
        deliverable_type="report",
        recipient="Marketing",
    )
    deliverable_repo.mark_delivered(deliverable["id"])

    conn.close()

Reading the audit trail
-----------------------

Every field changed via :meth:`~data_project_manager.db.repositories.project.ProjectRepository.update`
is recorded automatically when a :class:`~data_project_manager.db.repositories.changelog.ChangeLogRepository`
is injected:

.. code-block:: python

    from data_project_manager.db.repositories.changelog import ChangeLogRepository
    from data_project_manager.db.repositories.project import ProjectRepository

    conn = get_connection()
    changelog = ChangeLogRepository(conn)
    repo = ProjectRepository(conn, changelog=changelog)

    repo.update("2026-01-15-churn-analysis", status="done")

    for entry in changelog.list_for_entity("project", project["id"]):
        print(entry["field_name"], entry["old_value"], "->", entry["new_value"])
