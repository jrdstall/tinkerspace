"""Behaviour tests for CLI Work Order Courier.

Traces CLICOUR-01 through CLICOUR-05 per docs/design/specs/CLICOUR.md.
"""

from datetime import datetime, timezone
import io
from pathlib import Path
import sys

from iw.adapters.couriers.cli import CLICourier
from iw.contracts.courier import CourierProtocol
from iw.contracts.models import Author, AuthorKind, Node, UnitOfWork, UnitState
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.cli.main import handle_dispatch, handle_status, handle_submit


def _setup_store(tmp_path: Path) -> MarkdownStore:
    event_log = FileEventLog(log_path=tmp_path / "system" / "events.jsonl")
    return MarkdownStore(vault_dir=tmp_path, event_log=event_log)


def test_clicour_01_dispatch_command_seeds_folder_and_outputs_action_guide(tmp_path: Path, capsys):
    """CLICOUR-01: CLI dispatch transitions unit to dispatched and seeds work folder."""
    store = _setup_store(tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="test")

    unit = UnitOfWork(
        id="UOW-C01",
        title="Prior Art Survey",
        activity="prior-art-survey@1",
        state=UnitState.READY,
        subject_ids=["IDEA-A01"],
        action_guide="1. ASSIGNEE: Agent\n2. TASK: Search USPTO",
    )
    store.write_unit(unit, author=author)

    code = handle_dispatch(store, "UOW-C01", prompt="Search for low power display patents")
    assert code == 0

    reloaded = store.get_unit("UOW-C01")
    assert reloaded is not None
    assert reloaded.state == UnitState.DISPATCHED

    # Check work folder files
    folder = tmp_path / "work" / "UOW-C01"
    assert (folder / "prompt.md").exists()
    assert "Search for low power" in (folder / "prompt.md").read_text(encoding="utf-8")
    assert (folder / "deliverable.md").exists()

    # Check stdout captured
    out = capsys.readouterr().out
    assert "Dispatched UOW-C01" in out
    assert "Action Guide" in out


def test_clicour_02_submit_command_writes_deliverable_and_returns_unit(tmp_path: Path):
    """CLICOUR-02: CLI submit writes deliverable and transitions unit to returned."""
    store = _setup_store(tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="test")

    unit = UnitOfWork(
        id="UOW-C02",
        title="Bench Test",
        activity="trade-study@1",
        state=UnitState.READY,
        subject_ids=["IDEA-A01"],
    )
    store.write_unit(unit, author=author)

    deliv_text = "---\nunit: UOW-C02\nsummary: Bench power test complete\n---\n# Data\nPower is 40mW."
    code = handle_submit(store, "UOW-C02", deliverable=deliv_text, model="claude-3-7-sonnet")
    assert code == 0

    reloaded = store.get_unit("UOW-C02")
    assert reloaded is not None
    assert reloaded.state == UnitState.RETURNED

    folder = tmp_path / "work" / "UOW-C02"
    assert (folder / "deliverable.md").exists()
    assert "Power is 40mW." in (folder / "deliverable.md").read_text(encoding="utf-8")

    # Check attribution
    events = store.event_log.read_events()
    cli_events = [e for e in events if e.author and e.author.courier == "cli"]
    assert len(cli_events) > 0
    assert cli_events[-1].author.declared_model == "claude-3-7-sonnet"


def test_clicour_03_submit_with_accept_triggers_collection_and_accepts_unit(tmp_path: Path):
    """CLICOUR-03: CLI submit with --accept triggers collection pipeline and accepts unit."""
    store = _setup_store(tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="test")

    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Sunlight Display",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["display"],
        attrs={"scores": {"novel": 4, "works": 1, "reach": 1, "story": 1}, "cml": 1},
    )
    unit = UnitOfWork(
        id="UOW-C03",
        title="Display Feasibility",
        activity="trade-study@1",
        state=UnitState.READY,
        subject_ids=["IDEA-A01"],
    )
    store.write_node(idea, author=author)
    store.write_unit(unit, author=author)

    deliv_text = (
        "---\n"
        "unit: UOW-C03\n"
        "summary: Display feasibility validated on bench\n"
        "scores:\n"
        "  works: 4\n"
        "  reach: 3\n"
        "---\n"
        "# Feasibility Results\n"
    )
    code = handle_submit(store, "UOW-C03", deliverable=deliv_text, accept=True)
    assert code == 0

    reloaded_unit = store.get_unit("UOW-C03")
    assert reloaded_unit is not None
    assert reloaded_unit.state == UnitState.ACCEPTED

    reloaded_idea = store.get_node("IDEA-A01")
    assert reloaded_idea is not None
    assert reloaded_idea.attrs.get("scores", {}).get("works") == 4


def test_clicour_04_status_command_prints_lifecycle_states(tmp_path: Path, capsys):
    """CLICOUR-04: CLI status queries vault on-demand and prints units grouped by state."""
    store = _setup_store(tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="test")

    u1 = UnitOfWork(id="UOW-C01", title="Step 1", activity="act@1", state=UnitState.READY)
    u2 = UnitOfWork(id="UOW-C02", title="Step 2", activity="act@1", state=UnitState.DISPATCHED)
    store.write_unit(u1, author=author)
    store.write_unit(u2, author=author)

    code = handle_status(store)
    assert code == 0

    out = capsys.readouterr().out
    assert "Tinkerspace Work Units" in out
    assert "UOW-C01: Step 1" in out
    assert "UOW-C02: Step 2" in out
    assert "READY" in out
    assert "DISPATCHED" in out


def test_clicour_05_cli_courier_satisfies_courier_protocol(tmp_path: Path):
    """CLICOUR-05: CLICourier adapter satisfies CourierProtocol."""
    store = _setup_store(tmp_path)
    courier = CLICourier(store)

    assert isinstance(courier, CourierProtocol)
    assert courier.name == "cli"
