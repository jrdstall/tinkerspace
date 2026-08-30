"""Workflow runtime, DAG dependency validator, and ready-set evaluator.

Implements on-demand ready-set computation (DA-09 §02) and DAG execution without background engines.
"""

from pathlib import Path
from typing import Any

from iw.contracts.event_log import EventLogProtocol
from iw.contracts.models import Author, UnitOfWork, UnitState, Workflow
from iw.contracts.store import StoreProtocol
from iw.core.workflows import (
    atomic_write_workflow_yaml,
    read_workflow_yaml,
    scan_vault_workflows,
)
from iw.domain.workflow.state import transition_unit_state


def validate_dag(unit_ids: list[str], dependencies: dict[str, list[str]]) -> None:
    """Validate that the dependency graph has no unknown IDs or cycles (WORKFLOW-05)."""
    unit_id_set = {u.upper() for u in unit_ids}
    for unit, preds in dependencies.items():
        if unit.upper() not in unit_id_set:
            raise ValueError(f"Unknown unit ID '{unit}' in workflow dependencies")
        for pred in preds:
            if pred.upper() not in unit_id_set:
                raise ValueError(f"Unknown predecessor ID '{pred}' in workflow dependencies")

    # Cycle detection via depth-first search
    visited: set[str] = set()
    rec_stack: set[str] = set()

    def has_cycle(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)
        for neighbor in dependencies.get(node, []):
            clean_neighbor = neighbor.upper()
            if clean_neighbor not in visited:
                if has_cycle(clean_neighbor):
                    return True
            elif clean_neighbor in rec_stack:
                return True
        rec_stack.remove(node)
        return False

    for node in unit_id_set:
        if node not in visited:
            if has_cycle(node):
                raise ValueError(f"Workflow contains cyclic dependencies (WORKFLOW-05): cycle at {node}")


class WorkflowRuntime:
    """Layer 2 workflow coordinator managing workflows, DAG dependencies, and ready sets."""

    def __init__(self, store: StoreProtocol, vault_dir: Path, event_log: EventLogProtocol | None = None) -> None:
        self.store = store
        self.vault_dir = vault_dir
        self.event_log = event_log

    def create_workflow(self, workflow: Workflow, units: list[UnitOfWork], author: Author) -> Workflow:
        """Create a workflow, validate its DAG, and initialize root/blocked unit states."""
        if not author or not author.kind:
            raise ValueError("Author with kind is required to create workflow (WORKFLOW-06)")

        validate_dag(workflow.unit_ids, workflow.dependencies)
        folder = self.vault_dir / "work" / workflow.id.upper()
        atomic_write_workflow_yaml(folder, workflow)

        for unit in units:
            unit_id_upper = unit.id.upper()
            preds = workflow.dependencies.get(unit_id_upper, [])
            initial_state = UnitState.READY if len(preds) == 0 else UnitState.BLOCKED
            unit.state = initial_state
            unit.workflow_id = workflow.id.upper()
            self.store.write_unit(unit, author=author)

        if self.event_log:
            self.event_log.append("workflow_created", workflow.id.upper(), author, {"title": workflow.title})
        return workflow

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        """Fetch a workflow by ID from disk without caching."""
        target_id = workflow_id.strip().upper()
        wfl_file = self.vault_dir / "work" / target_id / "workflow.yaml"
        if wfl_file.exists():
            return read_workflow_yaml(wfl_file)
        for wfl in scan_vault_workflows(self.vault_dir):
            if wfl.id.upper() == target_id:
                return wfl
        return None

    def list_workflows(self) -> list[Workflow]:
        """Scan and return all workflows in the vault."""
        return scan_vault_workflows(self.vault_dir)

    def compute_ready_set(self, workflow_id: str | None = None) -> list[UnitOfWork]:
        """Compute all units eligible for dispatch without background watchers (WORKFLOW-03)."""
        all_units = self.store.list_units()
        unit_map = {u.id.upper(): u for u in all_units}
        ready_units: list[UnitOfWork] = []

        workflows = [self.get_workflow(workflow_id)] if workflow_id else self.list_workflows()
        wfl_map = {w.id.upper(): w for w in workflows if w is not None}

        for unit in all_units:
            if unit.state in (UnitState.ACCEPTED, UnitState.SKIPPED, UnitState.PARKED):
                continue
            if not unit.workflow_id:
                if unit.state in (UnitState.READY, UnitState.BLOCKED):
                    ready_units.append(unit)
                continue

            wfl = wfl_map.get(unit.workflow_id.upper())
            if not wfl:
                continue

            preds = wfl.dependencies.get(unit.id.upper(), [])
            pred_states = [unit_map[p.upper()].state for p in preds if p.upper() in unit_map]
            all_resolved = all(s in (UnitState.ACCEPTED, UnitState.SKIPPED) for s in pred_states)

            if all_resolved and unit.state in (UnitState.READY, UnitState.BLOCKED):
                ready_units.append(unit)

        return ready_units

    def refresh_workflow_states(self, workflow_id: str, author: Author) -> list[UnitOfWork]:
        """Evaluate dependencies and unblock ready units in the workflow (WORKFLOW-04)."""
        ready_set = self.compute_ready_set(workflow_id)
        updated_units: list[UnitOfWork] = []
        for unit in ready_set:
            if unit.state == UnitState.BLOCKED:
                transition_unit_state(unit, UnitState.READY, author=author, store=self.store)
                updated_units.append(unit)
        return updated_units
