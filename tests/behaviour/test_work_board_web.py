"""Behaviour tests for Work Board web UI and action endpoints.

Traces BOARD-01 through BOARD-06 per docs/design/specs/BOARD.md.
"""

from pathlib import Path
from starlette.testclient import TestClient
import yaml

from iw.contracts.models import Author, AuthorKind, UnitOfWork, UnitState
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.web.app import create_app


def _create_sample_unit(
    store: MarkdownStore,
    unit_id: str,
    title: str,
    state: UnitState,
    action_guide: str = "",
) -> UnitOfWork:
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    unit = UnitOfWork(
        id=unit_id,
        title=title,
        activity="prior-art-survey@1",
        state=state,
        subject_ids=["IDEA-A01"],
        action_guide=action_guide,
    )
    return store.write_unit(unit, author=author)


def test_board_01_work_board_renders_units_grouped_by_lifecycle_state(tmp_path: Path):
    """BOARD-01: The Work Board (/board) renders units grouped by lifecycle state."""
    store = MarkdownStore(vault_dir=tmp_path)
    _create_sample_unit(store, "UOW-A01", "Ready Survey", UnitState.READY)
    _create_sample_unit(store, "UOW-A02", "Dispatched Trade Study", UnitState.DISPATCHED)
    _create_sample_unit(store, "UOW-A03", "Returned Report", UnitState.RETURNED)
    _create_sample_unit(store, "UOW-A04", "Parked Concept", UnitState.PARKED)

    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/board")
    assert response.status_code == 200
    html = response.text

    assert "Work Board" in html
    assert "Ready Set" in html
    assert "In Progress" in html
    assert "Awaiting Review" in html
    assert "Parked" in html

    assert "UOW-A01" in html
    assert "Ready Survey" in html
    assert "UOW-A02" in html
    assert "Dispatched Trade Study" in html
    assert "UOW-A03" in html
    assert "Returned Report" in html
    assert "UOW-A04" in html
    assert "Parked Concept" in html


def test_board_02_ready_card_renders_action_guide_banner(tmp_path: Path):
    """BOARD-02: Ready unit cards prominently display the 5-point Action Guide banner."""
    store = MarkdownStore(vault_dir=tmp_path)
    guide_text = "1. ASSIGNEE: Jared (Human)\n2. INPUTS: ART-A01\n3. TASK: Trade study on displays\n4. OUTPUT: deliverable.md\n5. RESUME: Click Attach Result"
    _create_sample_unit(store, "UOW-A02", "Trade Study", UnitState.READY, action_guide=guide_text)

    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/board")
    assert response.status_code == 200
    html = response.text

    assert "ACTION GUIDE" in html
    assert "1. ASSIGNEE: Jared (Human)" in html
    assert "5. RESUME: Click Attach Result" in html


def test_board_03_dispatch_action_transitions_unit_to_dispatched(tmp_path: Path):
    """BOARD-03: Dispatching a ready unit transitions state to dispatched."""
    store = MarkdownStore(vault_dir=tmp_path)
    _create_sample_unit(store, "UOW-A03", "Dispatchable Task", UnitState.READY)

    app = create_app(store=store)
    client = TestClient(app, follow_redirects=False)

    response = client.post("/board/dispatch", data={"unit_id": "UOW-A03"})
    assert response.status_code == 303
    assert response.headers["location"] == "/board"

    updated = store.get_unit("UOW-A03")
    assert updated is not None
    assert updated.state == UnitState.DISPATCHED


def test_board_04_park_action_transitions_unit_to_parked(tmp_path: Path):
    """BOARD-04: Parking a unit transitions state to parked and removes it from ready set."""
    store = MarkdownStore(vault_dir=tmp_path)
    _create_sample_unit(store, "UOW-A04", "Parkable Task", UnitState.READY)

    app = create_app(store=store)
    client = TestClient(app, follow_redirects=False)

    response = client.post("/board/park", data={"unit_id": "UOW-A04"})
    assert response.status_code == 303

    updated = store.get_unit("UOW-A04")
    assert updated is not None
    assert updated.state == UnitState.PARKED


def test_board_05_skip_action_transitions_unit_to_skipped(tmp_path: Path):
    """BOARD-05: Skipping a unit transitions state to skipped."""
    store = MarkdownStore(vault_dir=tmp_path)
    _create_sample_unit(store, "UOW-A05", "Skippable Task", UnitState.READY)

    app = create_app(store=store)
    client = TestClient(app, follow_redirects=False)

    response = client.post("/board/skip", data={"unit_id": "UOW-A05"})
    assert response.status_code == 303

    updated = store.get_unit("UOW-A05")
    assert updated is not None
    assert updated.state == UnitState.SKIPPED


def test_board_06_board_loads_disk_state_on_demand_and_supports_refresh(tmp_path: Path):
    """BOARD-06: The board operates without watchers and supports an explicit refresh action."""
    store = MarkdownStore(vault_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    # Initial state: empty board
    res1 = client.get("/board")
    assert res1.status_code == 200
    assert "UOW-EXT01" not in res1.text

    # Write a new unit directly to disk (simulating synced arrival from another machine)
    unit_folder = tmp_path / "work" / "UOW-EXT01"
    unit_folder.mkdir(parents=True, exist_ok=True)
    raw_unit = {
        "id": "UOW-EXT01",
        "title": "External Synced Unit",
        "activity": "screening-assessment@1",
        "state": "ready",
        "subject_ids": ["IDEA-A01"],
    }
    (unit_folder / "unit.yaml").write_text(yaml.safe_dump(raw_unit), encoding="utf-8")

    # Explicitly trigger refresh state action
    refresh_res = client.post("/board/refresh", follow_redirects=True)
    assert refresh_res.status_code == 200
    assert "UOW-EXT01" in refresh_res.text
    assert "External Synced Unit" in refresh_res.text
