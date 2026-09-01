"""Contracts for the Maturation Planner service."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from iw.contracts.models import Author, AuthorKind, Node, Workflow


@dataclass(frozen=True)
class ActivityCatalogItem:
    """Represents an available activity template in the library."""

    id: str
    title: str
    category: str
    description: str
    advances: str | list[str] = "works"
    target_output: str = "deliverable.md"


@dataclass(frozen=True)
class PlanStep:
    """Represents a single step in a proposed maturation plan."""

    step_index: int
    title: str
    activity_id: str
    target_score: str  # novel | works | reach | story
    assignee_kind: AuthorKind
    size: str  # small | medium | large
    estimate_hours: float
    depends_on: list[int] = field(default_factory=list)
    reason: str = ""


@dataclass(frozen=True)
class MaturationPlan:
    """Represents a proposed sequence of activities to advance an idea's CML."""

    subject_id: str
    current_cml: int
    target_cml: int
    current_scores: dict[str, int]
    steps: list[PlanStep]
    rationale: str


@runtime_checkable
class PlannerProtocol(Protocol):
    """Protocol for the domain Planner service."""

    def draft_plan(
        self,
        node: Node,
        target_cml: int,
        custom_focus: str | None = None,
    ) -> MaturationPlan:
        """Draft a proposed maturation plan to advance a node to a target CML."""
        ...

    def list_activity_catalog(self) -> list[ActivityCatalogItem]:
        """List all available activity templates in the activity library."""
        ...

    def build_custom_plan(
        self,
        subject_id: str,
        steps: list[PlanStep],
        target_cml: int = 5,
        rationale: str = "Custom plan",
    ) -> MaturationPlan:
        """Build and validate a custom maturation plan authored by the user."""
        ...

    def instantiate_workflow(
        self,
        plan: MaturationPlan,
        author: Author,
    ) -> Workflow:
        """Instantiate a maturation plan into a runnable Workflow with Units of Work."""
        ...
