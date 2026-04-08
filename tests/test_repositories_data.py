"""Tests for db/repositories/data_file.py, deliverable.py, query.py, question.py."""

import sqlite3

import pytest
from helpers import fresh_conn, make_project

from data_project_manager.db.repositories.data_file import (
    AggregationLevelRepository,
    DataFileAggregationRepository,
    DataFileEntityTypeRepository,
    DataFileRepository,
    EntityTypeRepository,
)
from data_project_manager.db.repositories.deliverable import (
    DeliverableDataFileRepository,
    DeliverableRepository,
)
from data_project_manager.db.repositories.query import QueryRepository
from data_project_manager.db.repositories.question import RequestQuestionRepository

# ---------------------------------------------------------------------------
# EntityTypeRepository
# ---------------------------------------------------------------------------


class TestEntityTypeRepository:
    def test_list_returns_seed_data(self) -> None:
        conn = fresh_conn()
        repo = EntityTypeRepository(conn)
        types = repo.list()
        names = {t["name"] for t in types}
        assert {"customers", "transactions", "products"}.issubset(names)

    def test_get_by_name(self) -> None:
        conn = fresh_conn()
        repo = EntityTypeRepository(conn)
        et = repo.get_by_name("customers")
        assert et is not None
        assert et["name"] == "customers"

    def test_get_by_name_missing(self) -> None:
        conn = fresh_conn()
        repo = EntityTypeRepository(conn)
        assert repo.get_by_name("nonexistent") is None

    def test_create_custom(self) -> None:
        conn = fresh_conn()
        repo = EntityTypeRepository(conn)
        et = repo.create(name="invoices")
        assert et["name"] == "invoices"
        assert repo.get(et["id"]) == et

    def test_create_idempotent(self) -> None:
        conn = fresh_conn()
        repo = EntityTypeRepository(conn)
        a = repo.create(name="invoices")
        b = repo.create(name="invoices")
        assert a["id"] == b["id"]


# ---------------------------------------------------------------------------
# AggregationLevelRepository
# ---------------------------------------------------------------------------


class TestAggregationLevelRepository:
    def test_list_returns_seed_data(self) -> None:
        conn = fresh_conn()
        repo = AggregationLevelRepository(conn)
        levels = repo.list()
        names = {lvl["name"] for lvl in levels}
        assert {"row", "daily", "monthly", "summary"}.issubset(names)

    def test_get_by_name(self) -> None:
        conn = fresh_conn()
        repo = AggregationLevelRepository(conn)
        lvl = repo.get_by_name("monthly")
        assert lvl is not None
        assert lvl["name"] == "monthly"

    def test_create_custom(self) -> None:
        conn = fresh_conn()
        repo = AggregationLevelRepository(conn)
        lvl = repo.create(name="biannual")
        assert lvl["name"] == "biannual"

    def test_create_idempotent(self) -> None:
        conn = fresh_conn()
        repo = AggregationLevelRepository(conn)
        a = repo.create(name="biannual")
        b = repo.create(name="biannual")
        assert a["id"] == b["id"]


# ---------------------------------------------------------------------------
# DataFileRepository
# ---------------------------------------------------------------------------


class TestDataFileRepository:
    def test_create_minimal(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        repo = DataFileRepository(conn)
        f = repo.create(project_id=project["id"], file_path="data/raw/sales.csv")
        assert f["file_path"] == "data/raw/sales.csv"
        assert f["is_source"] == 1
        assert f["purged_at"] is None

    def test_create_all_fields(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        repo = DataFileRepository(conn)
        f = repo.create(
            project_id=project["id"],
            file_path="data/derived/sales_agg.parquet",
            file_format="parquet",
            sensitivity="internal",
            is_source=False,
            data_period_from="2026-01-01",
            data_period_to="2026-03-31",
            retention_date="2030-01-01",
        )
        assert f["file_format"] == "parquet"
        assert f["is_source"] == 0
        assert f["sensitivity"] == "internal"
        assert f["data_period_from"] == "2026-01-01"

    def test_get_existing(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        repo = DataFileRepository(conn)
        f = repo.create(project_id=project["id"], file_path="data/raw/x.csv")
        assert repo.get(f["id"]) == f

    def test_get_missing_returns_none(self) -> None:
        conn = fresh_conn()
        assert DataFileRepository(conn).get("no-such-id") is None

    def test_list_for_project(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        repo = DataFileRepository(conn)
        repo.create(project_id=project["id"], file_path="data/raw/b.csv")
        repo.create(project_id=project["id"], file_path="data/raw/a.csv")
        files = repo.list_for_project(project["id"])
        assert len(files) == 2
        assert files[0]["file_path"] == "data/raw/a.csv"

    def test_list_for_project_empty(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        assert DataFileRepository(conn).list_for_project(project["id"]) == []

    def test_mark_purged(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        repo = DataFileRepository(conn)
        f = repo.create(project_id=project["id"], file_path="data/raw/x.csv")
        updated = repo.mark_purged(f["id"])
        assert updated["purged_at"] is not None

    def test_mark_purged_missing_raises(self) -> None:
        conn = fresh_conn()
        with pytest.raises(ValueError, match="not found"):
            DataFileRepository(conn).mark_purged("no-such-id")


# ---------------------------------------------------------------------------
# DataFileEntityTypeRepository
# ---------------------------------------------------------------------------


class TestDataFileEntityTypeRepository:
    def _make_file(self, conn: sqlite3.Connection) -> dict:
        project = make_project(conn)
        return DataFileRepository(conn).create(
            project_id=project["id"], file_path="data/raw/x.csv"
        )

    def test_add_and_list(self) -> None:
        conn = fresh_conn()
        f = self._make_file(conn)
        et = EntityTypeRepository(conn).get_by_name("customers")
        junction = DataFileEntityTypeRepository(conn)
        junction.add(data_file_id=f["id"], entity_type_id=et["id"])
        result = junction.list_for_file(f["id"])
        assert len(result) == 1
        assert result[0]["name"] == "customers"

    def test_add_duplicate_ignored(self) -> None:
        conn = fresh_conn()
        f = self._make_file(conn)
        et = EntityTypeRepository(conn).get_by_name("customers")
        junction = DataFileEntityTypeRepository(conn)
        junction.add(data_file_id=f["id"], entity_type_id=et["id"])
        junction.add(data_file_id=f["id"], entity_type_id=et["id"])
        assert len(junction.list_for_file(f["id"])) == 1

    def test_remove(self) -> None:
        conn = fresh_conn()
        f = self._make_file(conn)
        et = EntityTypeRepository(conn).get_by_name("customers")
        junction = DataFileEntityTypeRepository(conn)
        junction.add(data_file_id=f["id"], entity_type_id=et["id"])
        junction.remove(data_file_id=f["id"], entity_type_id=et["id"])
        assert junction.list_for_file(f["id"]) == []

    def test_multiple_entity_types(self) -> None:
        conn = fresh_conn()
        f = self._make_file(conn)
        et_repo = EntityTypeRepository(conn)
        junction = DataFileEntityTypeRepository(conn)
        junction.add(
            data_file_id=f["id"], entity_type_id=et_repo.get_by_name("customers")["id"]
        )
        junction.add(
            data_file_id=f["id"],
            entity_type_id=et_repo.get_by_name("transactions")["id"],
        )
        names = {r["name"] for r in junction.list_for_file(f["id"])}
        assert names == {"customers", "transactions"}


# ---------------------------------------------------------------------------
# DataFileAggregationRepository
# ---------------------------------------------------------------------------


class TestDataFileAggregationRepository:
    def _make_file(self, conn: sqlite3.Connection) -> dict:
        project = make_project(conn)
        return DataFileRepository(conn).create(
            project_id=project["id"], file_path="data/raw/x.csv"
        )

    def test_add_and_list(self) -> None:
        conn = fresh_conn()
        f = self._make_file(conn)
        lvl = AggregationLevelRepository(conn).get_by_name("monthly")
        junction = DataFileAggregationRepository(conn)
        junction.add(data_file_id=f["id"], agg_level_id=lvl["id"])
        result = junction.list_for_file(f["id"])
        assert len(result) == 1
        assert result[0]["name"] == "monthly"

    def test_add_duplicate_ignored(self) -> None:
        conn = fresh_conn()
        f = self._make_file(conn)
        lvl = AggregationLevelRepository(conn).get_by_name("monthly")
        junction = DataFileAggregationRepository(conn)
        junction.add(data_file_id=f["id"], agg_level_id=lvl["id"])
        junction.add(data_file_id=f["id"], agg_level_id=lvl["id"])
        assert len(junction.list_for_file(f["id"])) == 1

    def test_remove(self) -> None:
        conn = fresh_conn()
        f = self._make_file(conn)
        lvl = AggregationLevelRepository(conn).get_by_name("monthly")
        junction = DataFileAggregationRepository(conn)
        junction.add(data_file_id=f["id"], agg_level_id=lvl["id"])
        junction.remove(data_file_id=f["id"], agg_level_id=lvl["id"])
        assert junction.list_for_file(f["id"]) == []


# ---------------------------------------------------------------------------
# QueryRepository
# ---------------------------------------------------------------------------


class TestQueryRepository:
    def test_create_minimal(self) -> None:
        conn = fresh_conn()
        repo = QueryRepository(conn)
        q = repo.create(query_path="queries/ltv.sql", language="sql")
        assert q["query_path"] == "queries/ltv.sql"
        assert q["language"] == "sql"
        assert q["executed_at"] is None

    def test_create_with_file_links(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        src = DataFileRepository(conn).create(
            project_id=project["id"], file_path="data/raw/x.csv"
        )
        out = DataFileRepository(conn).create(
            project_id=project["id"],
            file_path="data/derived/x_agg.parquet",
            is_source=False,
        )
        q = QueryRepository(conn).create(
            query_path="queries/agg.sql",
            language="sql",
            source_file_id=src["id"],
            output_file_id=out["id"],
        )
        assert q["source_file_id"] == src["id"]
        assert q["output_file_id"] == out["id"]

    def test_get_missing_returns_none(self) -> None:
        conn = fresh_conn()
        assert QueryRepository(conn).get("no-such-id") is None

    def test_list(self) -> None:
        conn = fresh_conn()
        repo = QueryRepository(conn)
        repo.create(query_path="queries/b.sql", language="sql")
        repo.create(query_path="queries/a.sql", language="sql")
        queries = repo.list()
        assert len(queries) == 2
        assert queries[0]["query_path"] == "queries/a.sql"

    def test_mark_executed(self) -> None:
        conn = fresh_conn()
        repo = QueryRepository(conn)
        q = repo.create(query_path="queries/ltv.sql", language="sql")
        updated = repo.mark_executed(q["id"])
        assert updated["executed_at"] is not None

    def test_mark_executed_missing_raises(self) -> None:
        conn = fresh_conn()
        with pytest.raises(ValueError, match="not found"):
            QueryRepository(conn).mark_executed("no-such-id")


# ---------------------------------------------------------------------------
# DeliverableRepository
# ---------------------------------------------------------------------------


class TestDeliverableRepository:
    def test_create_minimal(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        repo = DeliverableRepository(conn)
        d = repo.create(project_id=project["id"], type="report")
        assert d["type"] == "report"
        assert d["delivered_at"] is None

    def test_create_all_fields(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        repo = DeliverableRepository(conn)
        d = repo.create(
            project_id=project["id"],
            type="dashboard",
            file_path="output/dash.pbix",
            file_format="pbix",
            version="v2.0",
            delivered_at="2026-03-01T09:00:00+00:00",
        )
        assert d["file_format"] == "pbix"
        assert d["version"] == "v2.0"
        assert d["delivered_at"] == "2026-03-01T09:00:00+00:00"

    def test_get_missing_returns_none(self) -> None:
        conn = fresh_conn()
        assert DeliverableRepository(conn).get("no-such-id") is None

    def test_list_for_project_ordered(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        repo = DeliverableRepository(conn)
        repo.create(project_id=project["id"], type="report")
        repo.create(project_id=project["id"], type="dashboard")
        items = repo.list_for_project(project["id"])
        assert len(items) == 2

    def test_list_for_project_empty(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        assert DeliverableRepository(conn).list_for_project(project["id"]) == []

    def test_mark_delivered(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        repo = DeliverableRepository(conn)
        d = repo.create(project_id=project["id"], type="report")
        updated = repo.mark_delivered(d["id"])
        assert updated["delivered_at"] is not None

    def test_mark_delivered_missing_raises(self) -> None:
        conn = fresh_conn()
        with pytest.raises(ValueError, match="not found"):
            DeliverableRepository(conn).mark_delivered("no-such-id")


# ---------------------------------------------------------------------------
# DeliverableDataFileRepository
# ---------------------------------------------------------------------------


class TestDeliverableDataFileRepository:
    def test_add_and_list(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        d = DeliverableRepository(conn).create(project_id=project["id"], type="report")
        f = DataFileRepository(conn).create(
            project_id=project["id"], file_path="data/raw/x.csv"
        )
        junction = DeliverableDataFileRepository(conn)
        junction.add(deliverable_id=d["id"], data_file_id=f["id"])
        result = junction.list_for_deliverable(d["id"])
        assert len(result) == 1
        assert result[0]["file_path"] == "data/raw/x.csv"

    def test_add_duplicate_ignored(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        d = DeliverableRepository(conn).create(project_id=project["id"], type="report")
        f = DataFileRepository(conn).create(
            project_id=project["id"], file_path="data/raw/x.csv"
        )
        junction = DeliverableDataFileRepository(conn)
        junction.add(deliverable_id=d["id"], data_file_id=f["id"])
        junction.add(deliverable_id=d["id"], data_file_id=f["id"])
        assert len(junction.list_for_deliverable(d["id"])) == 1

    def test_remove(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        d = DeliverableRepository(conn).create(project_id=project["id"], type="report")
        f = DataFileRepository(conn).create(
            project_id=project["id"], file_path="data/raw/x.csv"
        )
        junction = DeliverableDataFileRepository(conn)
        junction.add(deliverable_id=d["id"], data_file_id=f["id"])
        junction.remove(deliverable_id=d["id"], data_file_id=f["id"])
        assert junction.list_for_deliverable(d["id"]) == []


# ---------------------------------------------------------------------------
# RequestQuestionRepository
# ---------------------------------------------------------------------------


class TestRequestQuestionRepository:
    def test_create_minimal(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        repo = RequestQuestionRepository(conn)
        q = repo.create(
            project_id=project["id"],
            question_text="What is the churn rate?",
        )
        assert q["question_text"] == "What is the churn rate?"
        assert q["data_period_from"] is None

    def test_create_with_period(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        repo = RequestQuestionRepository(conn)
        q = repo.create(
            project_id=project["id"],
            question_text="Monthly revenue Q1?",
            data_period_from="2026-01-01",
            data_period_to="2026-03-31",
        )
        assert q["data_period_from"] == "2026-01-01"
        assert q["data_period_to"] == "2026-03-31"

    def test_get_missing_returns_none(self) -> None:
        conn = fresh_conn()
        assert RequestQuestionRepository(conn).get("no-such-id") is None

    def test_list_for_project(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        repo = RequestQuestionRepository(conn)
        repo.create(project_id=project["id"], question_text="Q1?")
        repo.create(project_id=project["id"], question_text="Q2?")
        questions = repo.list_for_project(project["id"])
        assert len(questions) == 2

    def test_list_for_project_empty(self) -> None:
        conn = fresh_conn()
        project = make_project(conn)
        assert RequestQuestionRepository(conn).list_for_project(project["id"]) == []
