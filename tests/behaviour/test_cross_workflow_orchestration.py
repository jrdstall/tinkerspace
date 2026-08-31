"""Behaviour tests for Cross-Workflow Dependency Orchestration.

Traces CROSSWFL-01 through CROSSWFL-05 per docs/design/specs/CROSSWFL.md.
"""

from pathlib import Path
import pytest

from iw.contracts.models import Author, AuthorKind, UnitOfWork, UnitState, Workflow
from iw.core.store import MarkdownStore
from iw.domain.workflow.runtime import WorkflowRuntime, validate_dag
from iw.domain.workflow.state import transition_unit_state


def _setup_runtime(tmp_path: Path) -> tuple[MarkdownStore, WorkflowRuntime, Author]:
    store = MarkdownStore(vault_dir=tmp_path)
    runtime = WorkflowRuntime(store=store, vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="test")
    return store, runtime, author


def test_crosswfl_01_step_level_cross_workflow_dependency(tmp_path: Path):
    """CROSSWFL-01: Workflow steps can declare cross-workflow dependencies on units in other workflows."""
    store, runtime, author = _setup_runtime(tmp_path)

    # 1. Create Workflow A
    wfl_a = Workflow(id="WFL-A01", title="Workflow A", subject_ids=["IDEA-A01"], unit_ids=["UOW-A01"])
    u_a1 = UnitOfWork(id="UOW-A01", title="Step A1", activity="act@1", state=UnitState.READY)
    runtime.create_workflow(wfl_a, [u_a1], author=author)

    # 2. Create Workflow B depending on UOW-A01
    wfl_b = Workflow(
        id="WFL-B01",
        title="Workflow B",
        subject_ids=["IDEA-A01"],
        unit_ids=["UOW-B01"],
        dependencies={"UOW-B01": ["UOW-A01"]},
    )
    u_b1 = UnitOfWork(id="UOW-B01", title="Step B1", activity="act@1", state=UnitState.BLOCKED)
    runtime.create_workflow(wfl_b, [u_b1], author=author)

    # Step B1 is blocked waiting on UOW-A01
    ready = runtime.compute_ready_set("WFL-B01")
    assert len(ready) == 0


def test_crosswfl_02_whole_workflow_dependency_blocks_all_downstream_steps(tmp_path: Path):
    """CROSSWFL-02: Workflow with whole-workflow dependency blocks all steps until upstream completes."""
    store, runtime, author = _setup_runtime(tmp_path)

    wfl_a = Workflow(id="WFL-A01", title="Workflow A", subject_ids=["IDEA-A01"], unit_ids=["UOW-A01", "UOW-A02"])
    u_a1 = UnitOfWork(id="UOW-A01", title="Step A1", activity="act@1", state=UnitState.READY)
    u_a2 = UnitOfWork(id="UOW-A02", title="Step A2", activity="act@1", state=UnitState.BLOCKED)
    runtime.create_workflow(wfl_a, [u_a1, u_a2], author=author)

    wfl_b = Workflow(
        id="WFL-B01",
        title="Workflow B (Phase 2)",
        subject_ids=["IDEA-A01"],
        unit_ids=["UOW-B01"],
        workflow_dependencies=["WFL-A01"],
    )
    u_b1 = UnitOfWork(id="UOW-B01", title="Step B1 (Root of B)", activity="act@1", state=UnitState.BLOCKED)
    runtime.create_workflow(wfl_b, [u_b1], author=author)

    # Since Workflow A is not completed, Step B1 is not ready
    assert len(runtime.compute_ready_set("WFL-B01")) == 0


def test_crosswfl_03_global_cross_workflow_cycle_detection_rejects_cycles(tmp_path: Path):
    """CROSSWFL-03: Global multi-workflow validation rejects circular dependencies across workflows."""
    deps = {
        "UOW-A01": ["UOW-B01"],
        "UOW-B01": ["UOW-A01"],
    }
    with pytest.raises(ValueError, match="cyclic dependencies"):
        validate_dag(unit_ids=["UOW-A01", "UOW-B01"], dependencies=deps)


def test_crosswfl_04_on_demand_multi_workflow_ready_set_computation(tmp_path: Path):
    """CROSSWFL-04: compute_ready_set evaluates multi-workflow state on-demand without watchers."""
    store, runtime, author = _setup_runtime(tmp_path)

    wfl_a = Workflow(id="WFL-A01", title="WFL A", subject_ids=["IDEA-A01"], unit_ids=["UOW-A01"])
    u_a1 = UnitOfWork(id="UOW-A01", title="Step A1", activity="act@1", state=UnitState.READY)
    runtime.create_workflow(wfl_a, [u_a1], author=author)

    wfl_b = Workflow(id="WFL-B01", title="WFL B", subject_ids=["IDEA-A01"], unit_ids=["UOW-B01"])
    u_b1 = UnitOfWork(id="UOW-B01", title="Step B1", activity="act@1", state=UnitState.READY)
    runtime.create_workflow(wfl_b, [u_b1], author=author)

    # Calling with None evaluates global ready set across all workflows
    all_ready = runtime.compute_ready_set(None)
    ready_ids = {u.id for u in all_ready}
    assert "UOW-A01" in ready_ids
    assert "UOW-B01" in ready_ids


def test_crosswfl_05_completing_upstream_workflow_unblocks_downstream_ready_set(tmp_path: Path):
    """CROSSWFL-05: Accepting upstream prerequisite unblocks downstream workflow ready set."""
    store, runtime, author = _setup_runtime(tmp_path)

    wfl_a = Workflow(id="WFL-A01", title="WFL A", subject_ids=["IDEA-A01"], unit_ids=["UOW-A01"])
    u_a1 = UnitOfWork(id="UOW-A01", title="Step A1", activity="act@1", state=UnitState.READY)
    runtime.create_workflow(wfl_a, [u_a1], author=author)

    wfl_b = Workflow(
        id="WFL-B01",
        title="WFL B",
        subject_ids=["IDEA-A01"],
        unit_ids=["UOW-B01"],
        workflow_dependencies=["WFL-A01"],
    )
    u_b1 = UnitOfWork(id="UOW-B01", title="Step B1", activity="act@1", state=UnitState.BLOCKED)
    runtime.create_workflow(wfl_b, [u_b1], author=author)

    # Accept UOW-A01 to complete Workflow A
    u_a1_reloaded = store.get_unit("UOW-A01")
    assert u_a1_reloaded is not None
    transition_unit_state(u_a1_reloaded, UnitState.ACCEPTED, author=author, store=store)

    # Refresh Workflow B state
    unblocked = runtime.refresh_workflow_states("WFL-B01", author=author)
    assert len(unblocked) == 1
    assert unblocked[0].id == "UOW-B01"
    assert unblocked[0].state == UnitState.READY
