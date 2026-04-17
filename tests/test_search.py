"""Tests for the search engine (FTS5 + structured filters)."""

import sqlite3

import pytest
from helpers import fresh_conn

from data_project_manager.core.search import (
    _execute_metadata_search,
    _execute_search,
)
from data_project_manager.db.repositories.data_file import (
    AggregationLevelRepository,
    DataFileAggregationRepository,
    DataFileEntityTypeRepository,
    DataFileRepository,
    EntityTypeRepository,
)
from data_project_manager.db.repositories.deliverable import DeliverableRepository
from data_project_manager.db.repositories.person import (
    PersonRepository,
    ProjectPersonRepository,
)
from data_project_manager.db.repositories.project import ProjectRepository
from data_project_manager.db.repositories.question import RequestQuestionRepository
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


# ---------------------------------------------------------------------------
# Metadata (Tier 1 substring) search — issue #62
# ---------------------------------------------------------------------------


@pytest.fixture()
def metadata_conn() -> sqlite3.Connection:
    """Fresh DB seeded with metadata across every Tier 1 source."""
    conn = fresh_conn()
    projects = ProjectRepository(conn)
    tags = TagRepository(conn)
    ptags = ProjectTagRepository(conn)
    people = PersonRepository(conn)
    ppeople = ProjectPersonRepository(conn)
    data_files = DataFileRepository(conn)
    ets = EntityTypeRepository(conn)
    aggs = AggregationLevelRepository(conn)
    dfet = DataFileEntityTypeRepository(conn)
    dfa = DataFileAggregationRepository(conn)
    questions = RequestQuestionRepository(conn)
    deliverables = DeliverableRepository(conn)

    # Baseline project — matches nothing so it can be the "not found" control
    projects.create(
        title="Baseline",
        slug="2026-01-01-baseline",
        description="unrelated",
    )

    # Project matched only via tag
    p_tag = projects.create(title="P tag", slug="2026-01-02-p-tag")
    fraud = tags.create(name="fraud-detection")
    ptags.add(project_id=p_tag.id, tag_id=fraud.id)

    # Project matched only via person name/email, with a requestor role for filter test
    p_person = projects.create(title="P person", slug="2026-01-03-p-person")
    jane = people.create(
        first_name="Jane",
        last_name="Künzli",
        email="jane.k@example.com",
        department="Risk",
    )
    ppeople.add(project_id=p_person.id, person_id=jane.id, role="requestor")

    # Project matched only via entity type
    p_et = projects.create(title="P et", slug="2026-01-04-p-et")
    df_et = data_files.create(project_id=p_et.id, file_path="a.csv")
    customers = ets.get_by_name("customers")
    assert customers is not None
    dfet.add(data_file_id=df_et.id, entity_type_id=customers.id)

    # Project matched only via aggregation level
    p_agg = projects.create(title="P agg", slug="2026-01-05-p-agg")
    df_agg = data_files.create(project_id=p_agg.id, file_path="b.csv")
    quarterly = aggs.get_by_name("quarterly")
    assert quarterly is not None
    dfa.add(data_file_id=df_agg.id, agg_level_id=quarterly.id)

    # Project matched only via request question text
    p_q = projects.create(title="P question", slug="2026-01-06-p-question")
    questions.create(
        project_id=p_q.id,
        question_text="What is the retention uplift from the loyalty programme?",
    )

    # Project matched only via deliverable file path
    p_d = projects.create(title="P deliverable", slug="2026-01-07-p-deliverable")
    deliverables.create(
        project_id=p_d.id,
        type="report",
        file_path="output/annual-benchmark-2026.pdf",
    )

    # Project linked to a person row that has been retired (is_current=0).
    # This simulates SCD2 closure; the link must be excluded from person
    # substring matches.
    p_old = projects.create(title="P old person", slug="2026-01-08-p-old-person")
    bob = people.create(first_name="Bob", last_name="Obsolete")
    ppeople.add(project_id=p_old.id, person_id=bob.id, role="reviewer")
    conn.execute("UPDATE person SET is_current = 0 WHERE id = ?", (bob.id,))

    # Project with a literal percent sign in a question (LIKE-escape test)
    p_pct = projects.create(title="P pct", slug="2026-01-09-p-pct")
    questions.create(project_id=p_pct.id, question_text="Margin at 50% of target?")

    return conn


class TestMetadataSubstringSearch:
    """Each Tier 1 source surfaces projects on substring match."""

    def test_tag_name_match(self, metadata_conn: sqlite3.Connection) -> None:
        results = _execute_metadata_search(metadata_conn, query="fraud")
        assert [r.slug for r in results] == ["2026-01-02-p-tag"]

    def test_person_full_name_match(self, metadata_conn: sqlite3.Connection) -> None:
        results = _execute_metadata_search(metadata_conn, query="jane künzli")
        assert [r.slug for r in results] == ["2026-01-03-p-person"]

    def test_person_email_match(self, metadata_conn: sqlite3.Connection) -> None:
        results = _execute_metadata_search(metadata_conn, query="jane.k@example")
        assert [r.slug for r in results] == ["2026-01-03-p-person"]

    def test_entity_type_match(self, metadata_conn: sqlite3.Connection) -> None:
        results = _execute_metadata_search(metadata_conn, query="customers")
        assert [r.slug for r in results] == ["2026-01-04-p-et"]

    def test_aggregation_level_match(self, metadata_conn: sqlite3.Connection) -> None:
        results = _execute_metadata_search(metadata_conn, query="quarterly")
        assert [r.slug for r in results] == ["2026-01-05-p-agg"]

    def test_question_text_match(self, metadata_conn: sqlite3.Connection) -> None:
        results = _execute_metadata_search(metadata_conn, query="loyalty")
        assert [r.slug for r in results] == ["2026-01-06-p-question"]

    def test_deliverable_path_match(self, metadata_conn: sqlite3.Connection) -> None:
        results = _execute_metadata_search(metadata_conn, query="annual-benchmark")
        assert [r.slug for r in results] == ["2026-01-07-p-deliverable"]

    def test_case_insensitive(self, metadata_conn: sqlite3.Connection) -> None:
        results = _execute_metadata_search(metadata_conn, query="FRAUD")
        assert [r.slug for r in results] == ["2026-01-02-p-tag"]

    def test_scd2_old_version_excluded(self, metadata_conn: sqlite3.Connection) -> None:
        # Bob's person row has is_current=0; his name must not surface.
        results = _execute_metadata_search(metadata_conn, query="obsolete")
        assert results == []

    def test_like_wildcard_is_escaped(self, metadata_conn: sqlite3.Connection) -> None:
        # Literal "50%" should match only the question with "50%"; raw "%"
        # otherwise would match everything.
        results = _execute_metadata_search(metadata_conn, query="50%")
        assert [r.slug for r in results] == ["2026-01-09-p-pct"]

    def test_no_match(self, metadata_conn: sqlite3.Connection) -> None:
        results = _execute_metadata_search(metadata_conn, query="zzznope")
        assert results == []

    def test_exclude_ids(self, metadata_conn: sqlite3.Connection) -> None:
        first = _execute_metadata_search(metadata_conn, query="fraud")
        again = _execute_metadata_search(
            metadata_conn, query="fraud", exclude_ids=[r.id for r in first]
        )
        assert again == []


class TestMetadataFilters:
    """Structured filters apply on top of the Tier 1 substring."""

    def test_requestor_filter_on_search_projects(
        self, metadata_conn: sqlite3.Connection
    ) -> None:
        # FTS5 path: seeded project title "P person" is searchable; requestor
        # filter narrows to the same project.
        results = _execute_search(metadata_conn, query="person", requestor="jane")
        assert [r.slug for r in results] == ["2026-01-03-p-person"]

    def test_requestor_filter_excludes_non_requestor_role(
        self, metadata_conn: sqlite3.Connection
    ) -> None:
        # Bob's only link is role='reviewer' — filtering by requestor="bob"
        # must exclude his project.
        results = _execute_search(metadata_conn, requestor="bob")
        assert results == []

    def test_entity_type_filter(self, metadata_conn: sqlite3.Connection) -> None:
        results = _execute_search(metadata_conn, entity_types=["customers"])
        assert [r.slug for r in results] == ["2026-01-04-p-et"]

    def test_aggregation_level_filter(self, metadata_conn: sqlite3.Connection) -> None:
        results = _execute_search(metadata_conn, aggregation_levels=["quarterly"])
        assert [r.slug for r in results] == ["2026-01-05-p-agg"]

    def test_metadata_search_with_filter(
        self, metadata_conn: sqlite3.Connection
    ) -> None:
        # Substring match returns p_person; requestor filter keeps it;
        # requestor filter for a different name removes it.
        kept = _execute_metadata_search(metadata_conn, query="jane", requestor="jane")
        assert [r.slug for r in kept] == ["2026-01-03-p-person"]
        empty = _execute_metadata_search(metadata_conn, query="jane", requestor="alice")
        assert empty == []

    def test_metadata_search_filter_only(
        self, metadata_conn: sqlite3.Connection
    ) -> None:
        # No query, just filter — returns all projects matching the filter.
        results = _execute_metadata_search(metadata_conn, entity_types=["customers"])
        assert [r.slug for r in results] == ["2026-01-04-p-et"]
