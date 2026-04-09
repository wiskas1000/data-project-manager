"""Tests for db/repositories/changelog.py and its hooks."""

from helpers import fresh_conn, make_project

from data_project_manager.db.repositories.changelog import ChangeLogRepository
from data_project_manager.db.repositories.person import PersonRepository
from data_project_manager.db.repositories.project import ProjectRepository

# ---------------------------------------------------------------------------
# ChangeLogRepository — direct API
# ---------------------------------------------------------------------------


class TestChangeLogRepository:
    def test_log_and_get(self) -> None:
        conn = fresh_conn()
        repo = ChangeLogRepository(conn)
        project = make_project(conn)
        entry = repo.log(
            entity_type="project",
            entity_id=project.id,
            field_name="status",
            old_value="active",
            new_value="done",
        )
        assert entry.field_name == "status"
        assert entry.old_value == "active"
        assert entry.new_value == "done"
        assert entry.entity_type == "project"
        assert repo.get(entry.id) == entry

    def test_log_with_none_values(self) -> None:
        conn = fresh_conn()
        repo = ChangeLogRepository(conn)
        project = make_project(conn)
        entry = repo.log(
            entity_type="project",
            entity_id=project.id,
            field_name="description",
            old_value=None,
            new_value="First description",
        )
        assert entry.old_value is None
        assert entry.new_value == "First description"

    def test_get_missing_returns_none(self) -> None:
        conn = fresh_conn()
        assert ChangeLogRepository(conn).get("no-such-id") is None

    def test_list_for_entity(self) -> None:
        conn = fresh_conn()
        repo = ChangeLogRepository(conn)
        project = make_project(conn)
        repo.log(
            entity_type="project",
            entity_id=project.id,
            field_name="status",
            old_value="active",
            new_value="paused",
        )
        repo.log(
            entity_type="project",
            entity_id=project.id,
            field_name="domain",
            old_value=None,
            new_value="healthcare",
        )
        entries = repo.list_for_entity("project", project.id)
        assert len(entries) == 2
        field_names = {e.field_name for e in entries}
        assert field_names == {"status", "domain"}

    def test_list_for_entity_empty(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        assert ChangeLogRepository(conn).list_for_entity("project", project.id) == []

    def test_list_for_entity_scoped_to_entity(self) -> None:
        conn = fresh_conn()
        repo = ChangeLogRepository(conn)
        p1 = make_project(conn, "Alpha")
        p2 = make_project(conn, "Beta")
        repo.log(
            entity_type="project",
            entity_id=p1.id,
            field_name="status",
            old_value="active",
            new_value="done",
        )
        assert len(repo.list_for_entity("project", p2.id)) == 0

    def test_list_for_field(self) -> None:
        conn = fresh_conn()
        repo = ChangeLogRepository(conn)
        project = make_project(conn)
        repo.log(
            entity_type="project",
            entity_id=project.id,
            field_name="status",
            old_value="active",
            new_value="paused",
        )
        repo.log(
            entity_type="project",
            entity_id=project.id,
            field_name="status",
            old_value="paused",
            new_value="done",
        )
        repo.log(
            entity_type="project",
            entity_id=project.id,
            field_name="domain",
            old_value=None,
            new_value="finance",
        )
        status_history = repo.list_for_field("project", project.id, "status")
        assert len(status_history) == 2
        assert status_history[0].new_value == "paused"
        assert status_history[1].new_value == "done"

    def test_list_for_field_empty(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        assert (
            ChangeLogRepository(conn).list_for_field("project", project.id, "status")
            == []
        )

    def test_entries_ordered_by_changed_at(self) -> None:
        conn = fresh_conn()
        repo = ChangeLogRepository(conn)
        project = make_project(conn)
        repo.log(
            entity_type="project",
            entity_id=project.id,
            field_name="status",
            old_value="active",
            new_value="paused",
        )
        repo.log(
            entity_type="project",
            entity_id=project.id,
            field_name="status",
            old_value="paused",
            new_value="done",
        )
        entries = repo.list_for_entity("project", project.id)
        assert entries[0].changed_at <= entries[1].changed_at


# ---------------------------------------------------------------------------
# ProjectRepository — changelog hook
# ---------------------------------------------------------------------------


class TestProjectChangelogHook:
    def test_update_without_changelog_no_entries(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        ProjectRepository(conn).update(project.id, status="done")
        # No changelog wired up — table stays empty
        assert ChangeLogRepository(conn).list_for_entity("project", project.id) == []

    def test_update_logs_changed_field(self) -> None:
        conn = fresh_conn()
        changelog = ChangeLogRepository(conn)
        project = make_project(conn)
        ProjectRepository(conn, changelog=changelog).update(project.id, status="done")
        entries = changelog.list_for_entity("project", project.id)
        assert len(entries) == 1
        assert entries[0].field_name == "status"
        assert entries[0].old_value == "active"
        assert entries[0].new_value == "done"

    def test_update_logs_multiple_fields(self) -> None:
        conn = fresh_conn()
        changelog = ChangeLogRepository(conn)
        project = make_project(conn)
        ProjectRepository(conn, changelog=changelog).update(
            project.id, status="paused", domain="healthcare"
        )
        entries = changelog.list_for_entity("project", project.id)
        assert len(entries) == 2
        fields = {e.field_name for e in entries}
        assert fields == {"status", "domain"}

    def test_update_unchanged_field_not_logged(self) -> None:
        conn = fresh_conn()
        changelog = ChangeLogRepository(conn)
        project = make_project(conn)
        # status is already "active" — no change
        ProjectRepository(conn, changelog=changelog).update(project.id, status="active")
        assert changelog.list_for_entity("project", project.id) == []

    def test_update_logs_null_to_value(self) -> None:
        conn = fresh_conn()
        changelog = ChangeLogRepository(conn)
        project = make_project(conn)
        ProjectRepository(conn, changelog=changelog).update(
            project.id, description="New description"
        )
        entries = changelog.list_for_field("project", project.id, "description")
        assert len(entries) == 1
        assert entries[0].old_value is None
        assert entries[0].new_value == "New description"

    def test_multiple_updates_accumulate(self) -> None:
        conn = fresh_conn()
        changelog = ChangeLogRepository(conn)
        project = make_project(conn)
        repo = ProjectRepository(conn, changelog=changelog)
        repo.update(project.id, status="paused")
        repo.update(project.id, status="done")
        history = changelog.list_for_field("project", project.id, "status")
        assert len(history) == 2
        assert history[0].new_value == "paused"
        assert history[1].new_value == "done"

    def test_update_no_fields_no_log(self) -> None:
        conn = fresh_conn()
        changelog = ChangeLogRepository(conn)
        project = make_project(conn)
        ProjectRepository(conn, changelog=changelog).update(project.id)
        assert changelog.list_for_entity("project", project.id) == []


# ---------------------------------------------------------------------------
# PersonRepository — changelog hook
# ---------------------------------------------------------------------------


class TestPersonChangelogHook:
    def test_create_new_version_without_changelog_no_entries(self) -> None:
        conn = fresh_conn()
        repo = PersonRepository(conn)
        v1 = repo.create(first_name="Jane", last_name="Doe", department="Analytics")
        repo.create_new_version(v1.id, department="Data Science")
        assert ChangeLogRepository(conn).list_for_entity("person", v1.id) == []

    def test_create_new_version_logs_changed_field(self) -> None:
        conn = fresh_conn()
        changelog = ChangeLogRepository(conn)
        repo = PersonRepository(conn, changelog=changelog)
        v1 = repo.create(first_name="Jane", last_name="Doe", department="Analytics")
        v2 = repo.create_new_version(v1.id, department="Data Science")
        entries = changelog.list_for_entity("person", v2.id)
        assert len(entries) == 1
        assert entries[0].field_name == "department"
        assert entries[0].old_value == "Analytics"
        assert entries[0].new_value == "Data Science"

    def test_create_new_version_logs_multiple_fields(self) -> None:
        conn = fresh_conn()
        changelog = ChangeLogRepository(conn)
        repo = PersonRepository(conn, changelog=changelog)
        v1 = repo.create(
            first_name="Jane",
            last_name="Doe",
            function_title="Analyst",
            department="Analytics",
        )
        v2 = repo.create_new_version(
            v1.id, function_title="Senior Analyst", department="Data Science"
        )
        entries = changelog.list_for_entity("person", v2.id)
        assert len(entries) == 2
        fields = {e.field_name for e in entries}
        assert fields == {"function_title", "department"}

    def test_create_new_version_unchanged_fields_not_logged(self) -> None:
        conn = fresh_conn()
        changelog = ChangeLogRepository(conn)
        repo = PersonRepository(conn, changelog=changelog)
        v1 = repo.create(first_name="Jane", last_name="Doe", department="Analytics")
        v2 = repo.create_new_version(v1.id, department="Data Science")
        entries = changelog.list_for_entity("person", v2.id)
        # Only department changed; first_name and last_name are unchanged
        fields = {e.field_name for e in entries}
        assert "first_name" not in fields
        assert "last_name" not in fields

    def test_create_new_version_logs_null_to_value(self) -> None:
        conn = fresh_conn()
        changelog = ChangeLogRepository(conn)
        repo = PersonRepository(conn, changelog=changelog)
        v1 = repo.create(first_name="Jane", last_name="Doe")
        v2 = repo.create_new_version(v1.id, email="jane@example.com")
        entries = changelog.list_for_field("person", v2.id, "email")
        assert len(entries) == 1
        assert entries[0].old_value is None
        assert entries[0].new_value == "jane@example.com"
