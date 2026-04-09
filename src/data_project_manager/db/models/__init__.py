"""Dataclass models for all database entities.

Import from here for convenience::

    from data_project_manager.db.models import Project, Person, Tag
"""

from data_project_manager.db.models.changelog import ChangeLogEntry
from data_project_manager.db.models.data_file import (
    AggregationLevel,
    DataFile,
    EntityType,
)
from data_project_manager.db.models.deliverable import Deliverable
from data_project_manager.db.models.person import (
    Person,
    PersonWithRole,
    ProjectPersonLink,
)
from data_project_manager.db.models.project import Project
from data_project_manager.db.models.project_root import ProjectRoot
from data_project_manager.db.models.query import Query
from data_project_manager.db.models.question import RequestQuestion
from data_project_manager.db.models.search import SearchResult
from data_project_manager.db.models.tag import Tag

__all__ = [
    "AggregationLevel",
    "ChangeLogEntry",
    "DataFile",
    "Deliverable",
    "EntityType",
    "Person",
    "PersonWithRole",
    "Project",
    "ProjectPersonLink",
    "ProjectRoot",
    "Query",
    "RequestQuestion",
    "SearchResult",
    "Tag",
]
