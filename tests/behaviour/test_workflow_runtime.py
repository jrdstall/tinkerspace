"""Behaviour tests for Workflow DAG runtime and on-demand ready-set computation.

Traces WORKFLOW-01 through WORKFLOW-06 per docs/design/specs/WORKFLOW.md.
"""

from pathlib import Path
import pytest
import yaml

from iw.contracts.models import Author, AuthorKind, UnitOfWork, UnitState, Workflow
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.workflow.runtime import WorkflowRuntime
from iw.domain.workflow.state import transition_unit_state


def _sample_unit(unit_id: str, title: str) -> UnitOfWork:
    return UnitOfWork(
        id=unit_id,
        title=title,
        activity="prior-art-survey@1",
        state=UnitState.READY,
        subject_ids=["IDEA-A01"],
    )


def test_workflow_01_dag_stored_in_work_folder_as_workflow_yaml(tmp_path: Path):
    """WORKFLOW-01: A workflow is a DAG of dependency-linked units stored in work/<WFL-id>/workflow.yaml."""
    store = MarkdownStore(vault_dir=tmp_path)
    runtime = WorkflowRuntime(store=store, vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    wfl = Workflow(
        id="WFL-A01",
        title="Handlebar display maturation",
        subject_ids=["IDEA-A01"],
        unit_ids=["UOW-A01", "UOW-A02", "UOW-A03"],
        dependencies={"UOW-A02": ["UOW-A01"], "UOW-A03": ["UOW-A02"]},
    )
    units = [
        _sample_unit("UOW-A01", "Step 1: Prior Art"),
        _sample_unit("UOW-A02", "Step 2: Feasibility"),
        _sample_unit("UOW-A03", "Step 3: Screening"),
    ]

    saved_wfl = runtime.create_workflow(wfl, units, author=author)
    assert saved_wfl.id == "WFL-A01"

    wfl_file = tmp_path / "work" / "WFL-A01" / "workflow.yaml"
    assert wfl_file.exists()

    raw_data = yaml.safe_load(wfl_file.read_text(encoding="utf-8"))
    assert raw_data["id"] == "WFL-A01"
    assert raw_data["title"] == "Handlebar display maturation"
    assert raw_data["dependencies"]["UOW-A02"] == ["UOW-A01"]


def test_workflow_02_initialization_sets_roots_ready_and_dependents_blocked(tmp_path: Path):
    """WORKFLOW-02: Workflow instantiation initializes root units as ready and dependents as blocked."""
    store = MarkdownStore(vault_dir=tmp_path)
    runtime = WorkflowRuntime(store=store, vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    wfl = Workflow(
        id="WFL-A02",
        title="Multi-step linear pipeline",
        subject_ids=["IDEA-A01"],
        unit_ids=["UOW-A01", "UOW-A02", "UOW-A03"],
        dependencies={"UOW-A02": ["UOW-A01"], "UOW-A03": ["UOW-A02"]},
    )
    units = [
        _sample_unit("UOW-A01", "Step 1"),
        _sample_unit("UOW-A02", "Step 2"),
        _sample_unit("UOW-A03", "Step 3"),
    ]
    runtime.create_workflow(wfl, units, author=author)

    u1 = store.get_unit("UOW-A01")
    u2 = store.get_unit("UOW-A02")
    u3 = store.get_unit("UOW-A03")

    assert u1 is not None and u1.state == UnitState.READY
    assert u2 is not None and u2.state == UnitState.BLOCKED
    assert u3 is not None and u3.state == UnitState.BLOCKED


def test_workflow_03_compute_ready_set_evaluates_on_demand_without_watchers(tmp_path: Path):
    """WORKFLOW-03: compute_ready_set evaluates eligible units on-demand with zero background watchers."""
    store = MarkdownStore(vault_dir=tmp_path)
    runtime = WorkflowRuntime(store=store, vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    wfl = Workflow(
        id="WFL-A03",
        title="Ready set test",
        subject_ids=["IDEA-A01"],
        unit_ids=["UOW-A01", "UOW-A02"],
        dependencies={"UOW-A02": ["UOW-A01"]},
    )
    units = [_sample_unit("UOW-A01", "Root"), _sample_unit("UOW-A02", "Child")]
    runtime.create_workflow(wfl, units, author=author)

    # Add an independent standalone unit (not part of any workflow)
    standalone = _sample_unit("UOW-STANDALONE", "Standalone Task")
    store.write_unit(standalone, author=author)

    ready_set = runtime.compute_ready_set()
    ready_ids = {u.id for u in ready_set}

    assert "UOW-A01" in ready_ids
    assert "UOW-STANDALONE" in ready_ids
    assert "UOW-A02" not in ready_ids


def test_workflow_04_accepting_or_skipping_predecessor_unblocks_successor(tmp_path: Path):
    """WORKFLOW-04: Accepting or skipping a predecessor unblocks its immediate successors."""
    store = MarkdownStore(vault_dir=tmp_path)
    runtime = WorkflowRuntime(store=store, vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    wfl = Workflow(
        id="WFL-A04",
        title="Unblocking pipeline",
        subject_ids=["IDEA-A01"],
        unit_ids=["UOW-A01", "UOW-A02", "UOW-A03"],
        dependencies={"UOW-A02": ["UOW-A01"], "UOW-A03": ["UOW-A02"]},
    )
    units = [
        _sample_unit("UOW-A01", "Step 1"),
        _sample_unit("UOW-A02", "Step 2"),
        _sample_unit("UOW-A03", "Step 3"),
    ]
    runtime.create_workflow(wfl, units, author=author)

    # 1. Initially only UOW-A01 is ready
    assert [u.id for u in runtime.compute_ready_set("WFL-A04")] == ["UOW-A01"]

    # 2. Advance UOW-A01 to accepted (ready -> dispatched -> returned -> accepted)
    u1 = store.get_unit("UOW-A01")
    assert u1 is not None
    u1 = transition_unit_state(u1, UnitState.DISPATCHED, author, store)
    u1 = transition_unit_state(u1, UnitState.RETURNED, author, store)
    u1 = transition_unit_state(u1, UnitState.ACCEPTED, author, store)

    # 3. Ready set now includes UOW-A02
    ready_after_step1 = runtime.compute_ready_set("WFL-A04")
    assert [u.id for u in ready_after_step1] == ["UOW-A02"]

    # Refresh states transitions UOW-A02 from BLOCKED to READY
    unblocked = runtime.refresh_workflow_states("WFL-A04", author=author)
    assert len(unblocked) == 1
    assert unblocked[0].id == "UOW-A02"
    assert store.get_unit("UOW-A02").state == UnitState.READY

    # 4. Skip UOW-A02 (ready -> skipped)
    u2 = store.get_unit("UOW-A02")
    assert u2 is not None
    u2 = transition_unit_state(u2, UnitState.SKIPPED, author, store)

    # 5. Ready set now includes UOW-A03
    ready_after_step2 = runtime.compute_ready_set("WFL-A04")
    assert [u.id for u in ready_after_step2] == ["UOW-A03"]


def test_workflow_05_cyclic_dependencies_are_detected_and_rejected(tmp_path: Path):
    """WORKFLOW-05: Workflow DAG validation detects and rejects cyclic dependencies."""
    store = MarkdownStore(vault_dir=tmp_path)
    runtime = WorkflowRuntime(store=store, vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    cyclic_wfl = Workflow(
        id="WFL-CYCLE",
        title="Cyclic workflow",
        subject_ids=["IDEA-A01"],
        unit_ids=["UOW-A01", "UOW-A02", "UOW-A03"],
        dependencies={
            "UOW-A02": ["UOW-A01"],
            "UOW-A03": ["UOW-A02"],
            "UOW-A01": ["UOW-A03"],  # Cycle: 1 -> 2 -> 3 -> 1
        },
    )
    units = [
        _sample_unit("UOW-A01", "1"),
        _sample_unit("UOW-A02", "2"),
        _sample_unit("UOW-A03", "3"),
    ]

    with pytest.raises(ValueError, match="cyclic dependencies"):
        runtime.create_workflow(cyclic_wfl, units, author=author)


def test_workflow_06_workflow_writes_and_transitions_require_author_and_log_events(tmp_path: Path):
    """WORKFLOW-06: Workflow writes and state unblocking require author attribution and log events."""
    event_log = FileEventLog(log_path=tmp_path / "events.jsonl")
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log)
    runtime = WorkflowRuntime(store=store, vault_dir=tmp_path, event_log=event_log)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    wfl = Workflow(
        id="WFL-A06",
        title="Event emitter test",
        subject_ids=["IDEA-A01"],
        unit_ids=["UOW-A01"],
        dependencies={},
    )
    units = [_sample_unit("UOW-A01", "Single step")]

    # Author required
    with pytest.raises(ValueError, match="Author with kind is required"):
        runtime.create_workflow(wfl, units, author=None)  # type: ignore

    runtime.create_workflow(wfl, units, author=author)

    events = event_log.read_events()
    assert any(e.kind == "workflow_created" and e.subject_id == "WFL-A06" for e in events)
