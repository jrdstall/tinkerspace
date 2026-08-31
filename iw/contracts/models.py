"""Data structures and types for Innovator's Workspace contracts."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AuthorKind(str, Enum):
    HUMAN = "human"
    AGENT = "agent"
    TOOL = "tool"
    EXTERNAL = "external"


class UnitState(str, Enum):
    BLOCKED = "blocked"
    READY = "ready"
    DISPATCHED = "dispatched"
    RETURNED = "returned"
    ACCEPTED = "accepted"
    SKIPPED = "skipped"
    PARKED = "parked"


@dataclass(frozen=True)
class Author:
    """Attribution metadata required on every write."""
    kind: AuthorKind
    courier: str = "web-ui"
    requested_model: str | None = None
    declared_model: str | None = None


@dataclass
class Edge:
    """Typed relationship between two nodes (canonical or custom relation)."""
    from_id: str
    to_id: str
    relation: str
    created: datetime
    author: Author
    confidence: float = 1.0
    note: str = ""


@dataclass
class Node:
    """Primary typed entity in the corpus."""
    id: str
    type: str
    title: str
    created: datetime
    domain: str
    tags: list[str]
    state: str = "active"
    author: Author | None = None
    last_touched: datetime | None = None
    body: str = ""
    attrs: dict[str, Any] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)


@dataclass
class Artifact:
    """Concrete file/object acting as an input to or output from a step."""
    id: str
    role: str
    source_file: str
    produced_by: str | None = None
    input_to: list[str] = field(default_factory=list)
    rendered_file: str | None = None
    author: Author | None = None


@dataclass(frozen=True)
class NodeSummary:
    """Summary projection for search results and list views."""
    id: str
    type: str
    title: str
    domain: str
    tags: list[str]
    state: str
    cml: int = 1
    last_touched: datetime | None = None


@dataclass
class UnitOfWork:
    """Single executable task step."""
    id: str
    title: str
    activity: str
    state: UnitState
    subject_ids: list[str] = field(default_factory=list)
    workflow_id: str | None = None
    input_artifacts: list[str] = field(default_factory=list)
    assignee: dict[str, Any] = field(default_factory=dict)
    deliverable: dict[str, Any] = field(default_factory=dict)
    estimate: dict[str, Any] = field(default_factory=dict)
    template: str | None = None
    action_guide: str = ""


@dataclass
class Workflow:
    """Set of dependency-linked work units forming a DAG."""
    id: str
    title: str
    subject_ids: list[str]
    unit_ids: list[str]
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    workflow_dependencies: list[str] = field(default_factory=list)
    created: datetime = field(default_factory=datetime.now)
    template_id: str | None = None


@dataclass(frozen=True)
class InboxItem:
    """Raw captured thought before triage."""
    id: str
    raw_text: str
    created: datetime
    inlet: str = "quick-capture"
    source_filename: str | None = None


@dataclass(frozen=True)
class AttentionItem:
    """Quarantined unparseable file or sync conflict."""
    filepath: str
    reason: str
    detected_at: datetime


@dataclass(frozen=True)
class QueryFilters:
    """Search and filter criteria for the index."""
    type: str | None = None
    domain: str | None = None
    tag: str | None = None
    state: str | None = None
    min_cml: int | None = None


@dataclass(frozen=True)
class EventRecord:
    """Append-only audit and lifecycle record."""
    id: str
    timestamp: datetime
    kind: str
    subject_id: str | None = None
    author: Author | None = None
    payload: dict[str, Any] = field(default_factory=dict)

