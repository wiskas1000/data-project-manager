"""Tests for the search engine (FTS5 + structured filters)."""

import sqlite3

import pytest
from helpers import fresh_conn

from data_project_manager.core.search import _execute_search
from data_project_manager.db.repositories.project import ProjectRepository
from data_project_manager.db.repositories.tag import ProjectTagRepository, TagRepository


@pytest.fixture()
def search_conn() -> sqlite3.Connection:
    """Return a migrated connection with sample projects."""
    conn = fresh_conn()
    repo = ProjectRepository(conn)

    repo.create(
        title="Customer churn analysis",
        slug="2026-01-01-customer-churn-analysis",
        description="Predict customer attrition using logistic regression",
        domain="marketing",
        status="done",
    )
    repo.create(
        title="Hospital readmission study",
        slug="2026-02-15-hospital-readmission-study",
        description="Analyse 30-day readmission rates in cardiology",
        domain="healthcare",
        status="active",
    )
    repo.create(
        title="Quarterly sales report",
        slug="2026-03-01-quarterly-sales-report",
        description="Automated dashboard for Q1 revenue figures",
        domain="finance",
        status="active",
    )
    repo.create(
        title="Employee satisfaction survey",
        slug="2026-03-10-employee-satisfaction-survey",
        description="Analysis of annual engagement scores",
        domain="hr",
        status="paused",
    )
    repo.create(
        title="Churn prediction model v2",
        slug="2026-04-01-churn-prediction-model-v2",
        description="XGBoost model replacing the earlier logistic regression approach",
        domain="marketing",
        status="active",
    )

    # Tags
    tag_repo = TagRepository(conn)
    pt_repo = ProjectTagRepository(conn)

    ml_tag = tag_repo.create(name="machine-learning")
    lr_tag = tag_repo.create(name="logistic-regression")
    dash_tag = tag_repo.create(name="dashboard")

    # Tag the churn projects with ML tags
    p1 = repo.get_by_slug("2026-01-01-customer-churn-analysis")
    assert p1 is not None
    pt_repo.add(project_id=p1.id, tag_id=ml_tag.id)
    pt_repo.add(project_id=p1.id, tag_id=lr_tag.id)

    p5 = repo.get_by_slug("2026-04-01-churn-prediction-model-v2")
    assert p5 is not None
    pt_repo.add(project_id=p5.id, tag_id=ml_tag.id)

    # Tag the sales report
    p3 = repo.get_by_slug("2026-03-01-quarterly-sales-report")
    assert p3 is not None
    pt_repo.add(project_id=p3.id, tag_id=dash_tag.id)

    return conn


class TestFTS5TextSearch:
    """Full-text search via the FTS5 virtual table."""

    def test_search_by_title_word(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, query="churn")
        assert len(results) == 2
        slugs = {r.slug for r in results}
        assert "2026-01-01-customer-churn-analysis" in slugs
        assert "2026-04-01-churn-prediction-model-v2" in slugs

    def test_search_by_description_word(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, query="logistic")
        assert len(results) >= 1
        slugs = {r.slug for r in results}
        assert "2026-01-01-customer-churn-analysis" in slugs

    def test_search_by_domain_text(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, query="healthcare")
        assert len(results) == 1
        assert results[0].slug == "2026-02-15-hospital-readmission-study"

    def test_search_no_match(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, query="nonexistent")
        assert results == []

    def test_search_results_have_rank(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, query="churn")
        for r in results:
            assert isinstance(r.rank, float)

    def test_search_by_slug_text(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, query="quarterly")
        assert len(results) == 1
        assert results[0].slug == "2026-03-01-quarterly-sales-report"


class TestStructuredFilters:
    """Filtering by domain, status, tags, and date range."""

    def test_filter_by_domain(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, domain="marketing")
        assert len(results) == 2
        assert all(r.domain == "marketing" for r in results)

    def test_filter_by_status(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, status="active")
        assert len(results) == 3
        assert all(r.status == "active" for r in results)

    def test_filter_by_status_paused(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, status="paused")
        assert len(results) == 1
        assert results[0].slug == "2026-03-10-employee-satisfaction-survey"

    def test_filter_by_tag(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, tags=["machine-learning"])
        assert len(results) == 2
        slugs = {r.slug for r in results}
        assert "2026-01-01-customer-churn-analysis" in slugs
        assert "2026-04-01-churn-prediction-model-v2" in slugs

    def test_filter_by_multiple_tags(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(
            search_conn, tags=["machine-learning", "logistic-regression"]
        )
        assert len(results) == 1
        assert results[0].slug == "2026-01-01-customer-churn-analysis"

    def test_filter_by_date_from(self, search_conn: sqlite3.Connection) -> None:
        # All 5 projects created "now" — use a past date to include all
        results = _execute_search(search_conn, date_from="2020-01-01")
        assert len(results) == 5

    def test_filter_by_date_to(self, search_conn: sqlite3.Connection) -> None:
        # All projects created "now" — a far-future cutoff includes all
        results = _execute_search(search_conn, date_to="2099-12-31")
        assert len(results) == 5
        # A past cutoff includes none
        results_past = _execute_search(search_conn, date_to="2020-01-01")
        assert len(results_past) == 0

    def test_filter_by_date_range(self, search_conn: sqlite3.Connection) -> None:
        # Narrow range around "now" should find all test projects
        results = _execute_search(
            search_conn, date_from="2026-01-01", date_to="2099-12-31"
        )
        assert len(results) == 5


class TestCombinedSearch:
    """Text search combined with structured filters."""

    def test_text_and_domain(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, query="churn", domain="marketing")
        assert len(results) == 2

    def test_text_and_status(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, query="churn", status="done")
        assert len(results) == 1
        assert results[0].slug == "2026-01-01-customer-churn-analysis"

    def test_text_and_tag(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(
            search_conn, query="churn", tags=["logistic-regression"]
        )
        assert len(results) == 1
        assert results[0].slug == "2026-01-01-customer-churn-analysis"

    def test_domain_and_status(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, domain="marketing", status="active")
        assert len(results) == 1
        assert results[0].slug == "2026-04-01-churn-prediction-model-v2"


class TestFTSTriggerSync:
    """Verify FTS stays in sync after INSERT/UPDATE/DELETE."""

    def test_new_project_appears_in_search(
        self, search_conn: sqlite3.Connection
    ) -> None:
        repo = ProjectRepository(search_conn)
        repo.create(
            title="Fraud detection pipeline",
            slug="2026-05-01-fraud-detection-pipeline",
            domain="compliance",
        )
        results = _execute_search(search_conn, query="fraud")
        assert len(results) == 1
        assert results[0].slug == "2026-05-01-fraud-detection-pipeline"

    def test_updated_project_found_by_new_description(
        self, search_conn: sqlite3.Connection
    ) -> None:
        repo = ProjectRepository(search_conn)
        project = repo.get_by_slug("2026-03-01-quarterly-sales-report")
        assert project is not None
        repo.update(project.id, description="Revenue forecasting with ARIMA model")
        results = _execute_search(search_conn, query="ARIMA")
        assert len(results) == 1
        assert results[0].slug == "2026-03-01-quarterly-sales-report"

    def test_updated_project_old_text_still_works(
        self, search_conn: sqlite3.Connection
    ) -> None:
        repo = ProjectRepository(search_conn)
        project = repo.get_by_slug("2026-03-01-quarterly-sales-report")
        assert project is not None
        repo.update(project.id, description="New description")
        # Title search should still work
        results = _execute_search(search_conn, query="quarterly")
        assert len(results) == 1


class TestSearchResultModel:
    """Verify SearchResult dataclass properties."""

    def test_result_fields(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, query="hospital")
        assert len(results) == 1
        r = results[0]
        assert r.title == "Hospital readmission study"
        assert r.domain == "healthcare"
        assert r.status == "active"
        assert r.id is not None
        assert r.created_at is not None

    def test_result_is_frozen(self, search_conn: sqlite3.Connection) -> None:
        results = _execute_search(search_conn, query="hospital")
        with pytest.raises(AttributeError):
            results[0].title = "changed"  # type: ignore[misc]
