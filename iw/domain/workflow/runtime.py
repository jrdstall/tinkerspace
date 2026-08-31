"""Workflow runtime, DAG dependency validator, and ready-set evaluator.

Implements on-demand ready-set computation and cross-workflow DAG execution (CROSSWFL-01..05).
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


def validate_dag(
    unit_ids: list[str],
    dependencies: dict[str, list[str]],
    known_units: list[str] | None = None,
) -> None:
    """Validate that the dependency graph has no unknown IDs or cycles (WORKFLOW-05, CROSSWFL-03)."""
    local_set = {u.upper() for u in unit_ids}
    allowed_set = local_set if known_units is None else (local_set | {k.upper() for k in known_units})

    for unit, preds in dependencies.items():
        if unit.upper() not in local_set:
            raise ValueError(f"Unknown unit ID '{unit}' in workflow dependencies")
        for pred in preds:
            if pred.upper() not in allowed_set:
                raise ValueError(f"Unknown predecessor ID '{pred}' in workflow dependencies")

    visited: set[str] = set()
    rec_stack: set[str] = set()

    def has_cycle(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)
        for neighbor in dependencies.get(node, []):
            c_nbr = neighbor.upper()
            if c_nbr not in visited:
                if has_cycle(c_nbr):
                    return True
            elif c_nbr in rec_stack:
                return True
        rec_stack.remove(node)
        return False

    for node in dependencies:
        if node not in visited and has_cycle(node):
            raise ValueError(f"Workflow contains cyclic dependencies (WORKFLOW-05, CROSSWFL-03): cycle at {node}")


def _is_upstream_workflow_completed(wfl: Workflow, unit_map: dict[str, UnitOfWork]) -> bool:
    """Check if all units in an upstream workflow are accepted or skipped (CROSSWFL-02)."""
    for uid in wfl.unit_ids:
        u = unit_map.get(uid.upper())
        if not u or u.state not in (UnitState.ACCEPTED, UnitState.SKIPPED):
            return False
    return True


def _is_unit_ready(unit: UnitOfWork, unit_map: dict[str, UnitOfWork], wfl_map: dict[str, Workflow]) -> bool:
    """Evaluate whether a unit's workflow and predecessor dependencies are met (CROSSWFL-01, 02)."""
    if not unit.workflow_id:
        return unit.state in (UnitState.READY, UnitState.BLOCKED)

    wfl = wfl_map.get(unit.workflow_id.upper())
    if not wfl:
        return False

    for parent_wfl_id in wfl.workflow_dependencies:
        parent_wfl = wfl_map.get(parent_wfl_id.upper())
        if not parent_wfl or not _is_upstream_workflow_completed(parent_wfl, unit_map):
            return False

    preds = wfl.dependencies.get(unit.id.upper(), [])
    pred_states = [unit_map[p.upper()].state for p in preds if p.upper() in unit_map]
    return len(pred_states) == len(preds) and all(s in (UnitState.ACCEPTED, UnitState.SKIPPED) for s in pred_states)


class WorkflowRuntime:
    """Layer 2 workflow coordinator managing workflows, DAG dependencies, and ready sets."""

    def __init__(self, store: StoreProtocol, vault_dir: Path, event_log: EventLogProtocol | None = None) -> None:
        self.store = store
        self.vault_dir = vault_dir
        self.event_log = event_log

    def create_workflow(self, workflow: Workflow, units: list[UnitOfWork], author: Author) -> Workflow:
        """Create a workflow, validate its DAG, and initialize unit states (CROSSWFL-01..03)."""
        if not author or not author.kind:
            raise ValueError("Author with kind is required to create workflow (WORKFLOW-06)")

        existing_unit_ids = [u.id for u in self.store.list_units()]
        validate_dag(workflow.unit_ids, workflow.dependencies, known_units=existing_unit_ids)
        folder = self.vault_dir / "work" / workflow.id.upper()
        atomic_write_workflow_yaml(folder, workflow)

        for unit in units:
            preds = workflow.dependencies.get(unit.id.upper(), [])
            has_unresolved_preds = len(preds) > 0 or len(workflow.workflow_dependencies) > 0
            unit.state = UnitState.BLOCKED if has_unresolved_preds else UnitState.READY
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
        """Compute all units eligible for dispatch without background watchers (CROSSWFL-04)."""
        all_units = self.store.list_units()
        unit_map = {u.id.upper(): u for u in all_units}
        wfl_map = {w.id.upper(): w for w in self.list_workflows()}
        filter_wfl_id = workflow_id.strip().upper() if workflow_id else None

        ready_units: list[UnitOfWork] = []
        for unit in all_units:
            if unit.state in (UnitState.ACCEPTED, UnitState.SKIPPED, UnitState.PARKED):
                continue
            if filter_wfl_id and (not unit.workflow_id or unit.workflow_id.upper() != filter_wfl_id):
                continue
            if _is_unit_ready(unit, unit_map, wfl_map) and unit.state in (UnitState.READY, UnitState.BLOCKED):
                ready_units.append(unit)

        return ready_units

    def refresh_workflow_states(self, workflow_id: str, author: Author) -> list[UnitOfWork]:
        """Evaluate dependencies and unblock ready units in the workflow (CROSSWFL-05)."""
        ready_set = self.compute_ready_set(workflow_id)
        updated_units: list[UnitOfWork] = []
        for unit in ready_set:
            if unit.state == UnitState.BLOCKED:
                transition_unit_state(unit, UnitState.READY, author=author, store=self.store)
                updated_units.append(unit)
        return updated_units
