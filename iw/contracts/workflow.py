"""Workflow runtime protocol definition."""

from typing import Protocol, runtime_checkable
from iw.contracts.models import Author, UnitOfWork, Workflow


@runtime_checkable
class WorkflowProtocol(Protocol):
    """Layer 2 workflow runtime for managing units of work and templates."""

    def instantiate_template(self, template_id: str, subject_ids: list[str]) -> Workflow:
        """Instantiate an activity template into a workflow of work units."""
        ...

    def compute_ready_set(self, workflow_id: str) -> list[UnitOfWork]:
        """Compute all work units whose upstream dependencies are accepted."""
        ...

    def dispatch_unit(self, unit_id: str, courier_name: str) -> str:
        """Dispatch a unit of work to an assigned worker via a named courier."""
        ...

    def collect_unit_results(self, unit_id: str, author: Author) -> UnitOfWork:
        """Scan a unit's folder on disk, ingest output artifacts, and update state."""
        ...
