"""Unit-of-work lifecycle and storage behaviour tests.

Traces UOW-01 through UOW-08 per docs/design/specs/UOW.md.
"""

from pathlib import Path
import pytest
import yaml

from iw.contracts.models import Author, AuthorKind, UnitOfWork, UnitState
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.workflow.state import can_transition, transition_unit_state


def _sample_unit(unit_id: str = "UOW-A01", state: UnitState = UnitState.READY) -> UnitOfWork:
    return UnitOfWork(
        id=unit_id,
        title="Prior art survey for handlebar display",
        activity="prior-art-survey@1",
        state=state,
        subject_ids=["IDEA-A01"],
        workflow_id="WFL-A01",
        input_artifacts=["ART-A01"],
        assignee={"kind": "agent", "name": "claude-3-5-sonnet"},
        deliverable={"target_file": f"work/{unit_id}/deliverable.md", "format": "markdown"},
        estimate={"size_hint": "small"},
        template="prior-art-survey@1",
        action_guide="1. ASSIGNEE: Agent\n2. INPUTS: ART-A01\n3. TASK: Survey prior art\n4. OUTPUT: deliverable.md\n5. RESUME: Call submit_result",
    )


def test_uow_01_unit_saved_in_work_folder_as_unit_yaml(tmp_path: Path):
    """UOW-01: A unit of work is stored in structured work/<UOW-id>/unit.yaml."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    unit = _sample_unit("UOW-A01", UnitState.READY)

    written = store.write_unit(unit, author=author)
    assert written.id == "UOW-A01"

    unit_yaml_path = tmp_path / "work" / "UOW-A01" / "unit.yaml"
    assert unit_yaml_path.exists()

    raw_data = yaml.safe_load(unit_yaml_path.read_text(encoding="utf-8"))
    assert raw_data["id"] == "UOW-A01"
    assert raw_data["state"] == "ready"
    assert raw_data["activity"] == "prior-art-survey@1"
    assert raw_data["subject_ids"] == ["IDEA-A01"]


def test_uow_02_unit_states_enum_coverage():
    """UOW-02: A unit of work has one of seven explicit states."""
    expected_states = {"blocked", "ready", "dispatched", "returned", "accepted", "skipped", "parked"}
    actual_states = {s.value for s in UnitState}
    assert actual_states == expected_states


def test_uow_03_state_transitions_enforce_lifecycle_rules(tmp_path: Path):
    """UOW-03: State transitions follow the DA-09 state machine and reject invalid transitions."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    # 1. Start blocked -> ready -> dispatched -> returned -> accepted (valid sequence)
    unit = _sample_unit("UOW-A01", UnitState.BLOCKED)
    store.write_unit(unit, author=author)

    unit = transition_unit_state(unit, UnitState.READY, author, store)
    assert unit.state == UnitState.READY

    unit = transition_unit_state(unit, UnitState.DISPATCHED, author, store)
    assert unit.state == UnitState.DISPATCHED

    unit = transition_unit_state(unit, UnitState.RETURNED, author, store)
    assert unit.state == UnitState.RETURNED

    unit = transition_unit_state(unit, UnitState.ACCEPTED, author, store)
    assert unit.state == UnitState.ACCEPTED

    # 2. Terminal state accepted cannot transition to anything
    assert not can_transition(UnitState.ACCEPTED, UnitState.READY)
    with pytest.raises(ValueError, match="Invalid state transition"):
        transition_unit_state(unit, UnitState.READY, author, store)


def test_uow_04_writing_unit_yaml_is_atomic_and_uncached(tmp_path: Path):
    """UOW-04: Writing unit.yaml is atomic and reading always hits disk without caching."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    unit = _sample_unit("UOW-A04", UnitState.READY)
    store.write_unit(unit, author=author)

    # Check atomic write left no temporary files
    temp_files = list((tmp_path / "work" / "UOW-A04").glob("*.tmp"))
    assert len(temp_files) == 0

    # Modify unit.yaml directly on disk (simulating external edit)
    unit_yaml_path = tmp_path / "work" / "UOW-A04" / "unit.yaml"
    raw_text = unit_yaml_path.read_text(encoding="utf-8")
    unit_yaml_path.write_text(raw_text.replace("Prior art survey", "External disk edit survey"), encoding="utf-8")

    # Re-reading unit returns fresh disk state without caching
    reloaded = store.get_unit("UOW-A04")
    assert reloaded is not None
    assert "External disk edit survey" in reloaded.title


def test_uow_05_state_transition_emits_event_record(tmp_path: Path):
    """UOW-05: State transitions emit unit_written records to the event log."""
    event_log = FileEventLog(log_path=tmp_path / "events.jsonl")
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    unit = _sample_unit("UOW-A05", UnitState.READY)
    store.write_unit(unit, author=author)
    transition_unit_state(unit, UnitState.DISPATCHED, author, store)

    events = event_log.read_events()
    assert len(events) == 2
    assert events[0].kind == "unit_written"
    assert events[0].subject_id == "UOW-A05"
    assert events[1].payload["state"] == "dispatched"


def test_uow_06_case_insensitive_unit_lookup(tmp_path: Path):
    """UOW-06: Unit lookups by ID are case-insensitive on input."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    unit = _sample_unit("UOW-A06", UnitState.READY)
    store.write_unit(unit, author=author)

    lower_fetch = store.get_unit("uow-a06")
    upper_fetch = store.get_unit("UOW-A06")
    mixed_fetch = store.get_unit("UoW-a06")

    assert lower_fetch is not None
    assert upper_fetch is not None
    assert mixed_fetch is not None
    assert lower_fetch.id == "UOW-A06"
    assert upper_fetch.id == "UOW-A06"
    assert mixed_fetch.id == "UOW-A06"


def test_uow_07_list_units_discovers_all_work_folders(tmp_path: Path):
    """UOW-07: Scanning units discovers all work/UOW-*/unit.yaml folders across the vault."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    unit1 = _sample_unit("UOW-A01", UnitState.READY)
    unit2 = _sample_unit("UOW-A02", UnitState.BLOCKED)
    unit3 = _sample_unit("UOW-A03", UnitState.PARKED)

    store.write_unit(unit1, author=author)
    store.write_unit(unit2, author=author)
    store.write_unit(unit3, author=author)

    all_units = store.list_units()
    assert len(all_units) == 3
    unit_ids = {u.id for u in all_units}
    assert unit_ids == {"UOW-A01", "UOW-A02", "UOW-A03"}


def test_uow_08_author_attribution_required_on_write(tmp_path: Path):
    """UOW-08: Every unit write and state transition requires explicit author attribution."""
    store = MarkdownStore(vault_dir=tmp_path)
    unit = _sample_unit("UOW-A08", UnitState.READY)

    with pytest.raises(ValueError, match="Author with kind is required"):
        store.write_unit(unit, author=None)  # type: ignore

    with pytest.raises(ValueError, match="Author with kind is required"):
        transition_unit_state(unit, UnitState.DISPATCHED, author=None, store=store)  # type: ignore
