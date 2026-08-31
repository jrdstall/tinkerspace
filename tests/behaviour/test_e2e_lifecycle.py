"""End-to-End System Verification and Lifecycle Integration Suite.

Traces E2E-01 through E2E-05 per docs/design/specs/E2E.md.
Exercises the entire Tinkerspace toolchain without mocks.
"""

from datetime import datetime, timezone
from pathlib import Path

from iw.adapters.couriers.cli import CLICourier
from iw.contracts.models import Author, AuthorKind, Node, UnitOfWork, UnitState, Workflow
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.core.triage import TriageService
from iw.domain.intake.external import ingest_external_node
from iw.domain.workflow.collection import collect_unit_results
from iw.domain.workflow.runtime import WorkflowRuntime
from iw.domain.workflow.state import transition_unit_state
from iw.mcp.server import submit_result_tool


def _setup_system(tmp_path: Path) -> tuple[MarkdownStore, WorkflowRuntime, Author]:
    event_log = FileEventLog(log_path=tmp_path / "system" / "events.jsonl")
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log)
    runtime = WorkflowRuntime(store=store, vault_dir=tmp_path, event_log=event_log)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    return store, runtime, author


def test_e2e_01_raw_capture_to_triage_idea_with_cml(tmp_path: Path):
    """E2E-01: Raw thought capture to triage into typed idea note with CML derivation."""
    store, _, author = _setup_system(tmp_path)
    triage = TriageService(store=store)

    # 1. Quick capture
    item = store.append_inbox(
        raw_text="Low power sunlight readable display for mountain bike handlebar navigation",
        inlet="quick-capture",
    )
    assert item is not None
    assert len(store.list_inbox()) == 1

    # 2. Triage into Idea node
    idea_stub = Node(
        id="",
        type="idea",
        title="Sunlight Readable Handlebar Display",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["display", "mtb", "optics"],
        attrs={"scores": {"novel": 3, "works": 1, "reach": 4, "story": 2}},
    )
    idea = triage.triage_item(
        item_id=item.id,
        node=idea_stub,
        author=author,
    )
    assert idea is not None
    assert idea.id == "IDEA-A01"
    assert idea.attrs.get("cml") == 1
    assert len(store.list_inbox()) == 0


def test_e2e_02_workflow_creation_and_ready_set(tmp_path: Path):
    """E2E-02: Workflow creation with dependency graph and on-demand ready-set computation."""
    store, runtime, author = _setup_system(tmp_path)

    wfl = Workflow(
        id="WFL-A01",
        title="Display Feasibility & Prototyping",
        subject_ids=["IDEA-A01"],
        unit_ids=["UOW-A01", "UOW-A02"],
        dependencies={"UOW-A02": ["UOW-A01"]},
    )
    u1 = UnitOfWork(id="UOW-A01", title="Display Trade Study", activity="trade-study@1", state=UnitState.READY, subject_ids=["IDEA-A01"])
    u2 = UnitOfWork(id="UOW-A02", title="Mechanical Enclosure CAD", activity="cad-model@1", state=UnitState.BLOCKED, subject_ids=["IDEA-A01"])

    created_wfl = runtime.create_workflow(wfl, [u1, u2], author=author)
    assert created_wfl.id == "WFL-A01"

    ready_set = runtime.compute_ready_set("WFL-A01")
    assert len(ready_set) == 1
    assert ready_set[0].id == "UOW-A01"


def test_e2e_03_courier_dispatch_and_execution(tmp_path: Path):
    """E2E-03: Work unit dispatch via CLI/MCP and deliverable submission with attribution."""
    store, _, author = _setup_system(tmp_path)
    courier = CLICourier(store=store, vault_dir=tmp_path)

    u1 = UnitOfWork(id="UOW-A01", title="Display Trade Study", activity="trade-study@1", state=UnitState.READY, subject_ids=["IDEA-A01"])
    store.write_unit(u1, author=author)

    # 1. Dispatch
    courier.deliver_order("UOW-A01", {"prompt": "Perform display trade study between OLED, Memory LCD, and Transflective"})

    # 2. Agent submits deliverable via MCP safe tool
    deliv_content = (
        "---\n"
        "unit: UOW-A01\n"
        "summary: Memory LCD selected for sub-100mW power profile and direct sunlight visibility\n"
        "scores:\n"
        "  novel: 4\n"
        "  works: 4\n"
        "  reach: 3\n"
        "  story: 2\n"
        "verdict: go\n"
        "---\n"
        "# Trade Study Report\n"
        "Memory LCD is ideal."
    )
    submit_result_tool(
        store=store,
        unit_id="UOW-A01",
        deliverable=deliv_content,
        artifacts=[{"filename": "optical_stack.svg", "content": "<svg><rect width='100' height='100'/></svg>"}],
        model_name="claude-3-7-sonnet",
    )

    reloaded_unit = store.get_unit("UOW-A01")
    assert reloaded_unit is not None
    assert reloaded_unit.state == UnitState.RETURNED


def test_e2e_04_collection_pipeline_materializes_scores_and_cml(tmp_path: Path):
    """E2E-04: Result collection parses scores, registers artifacts via Open Hospitality, and updates CML."""
    store, runtime, author = _setup_system(tmp_path)

    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Sunlight Readable Handlebar Display",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["display"],
        attrs={"scores": {"novel": 3, "works": 1, "reach": 4, "story": 2}, "cml": 1},
    )
    store.write_node(idea, author=author)

    # Work folder contains deliverable and companion files
    folder = tmp_path / "work" / "UOW-A01"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "deliverable.md").write_text(
        "---\nunit: UOW-A01\nsummary: Feasibility proven\nscores:\n  works: 4\n  reach: 3\nverdict: go\n---\n# Done",
        encoding="utf-8",
    )
    (folder / "diagram.svg").write_text("<svg/>", encoding="utf-8")

    u1 = UnitOfWork(id="UOW-A01", title="Trade Study", activity="trade-study@1", state=UnitState.RETURNED, subject_ids=["IDEA-A01"])
    store.write_unit(u1, author=author)

    # Collect result
    unit, artifacts = collect_unit_results(store=store, unit_id="UOW-A01", author=author)
    assert len(artifacts) >= 1
    assert unit.state == UnitState.ACCEPTED

    # Verify Idea node updated
    updated_idea = store.get_node("IDEA-A01")
    assert updated_idea is not None
    assert updated_idea.attrs["scores"]["works"] == 4
    assert updated_idea.attrs["cml"] == 2
    assert updated_idea.attrs["screening_verdict"] == "go"


def test_e2e_05_cross_workflow_progression_and_external_intake(tmp_path: Path):
    """E2E-05: Downstream workflow unblocking and external foreign vault note ingestion."""
    store, runtime, author = _setup_system(tmp_path)

    # 0. Local pre-existing Idea node
    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Local Idea",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["local"],
    )
    store.write_node(idea, author=author)

    # 1. Create and complete upstream workflow
    wfl_a = Workflow(id="WFL-A01", title="Upstream Phase", subject_ids=["IDEA-A01"], unit_ids=["UOW-A01"])
    u1 = UnitOfWork(id="UOW-A01", title="Step 1", activity="act@1", state=UnitState.READY, subject_ids=["IDEA-A01"])
    runtime.create_workflow(wfl_a, [u1], author=author)

    # 2. Downstream workflow starts BLOCKED
    wfl_b = Workflow(id="WFL-B01", title="Downstream Phase", subject_ids=["IDEA-A01"], unit_ids=["UOW-B01"], workflow_dependencies=["WFL-A01"])
    u2 = UnitOfWork(id="UOW-B01", title="Step 2", activity="act@1", state=UnitState.BLOCKED, subject_ids=["IDEA-A01"])
    runtime.create_workflow(wfl_b, [u2], author=author)

    # Transition UOW-A01 to ACCEPTED
    u1_reloaded = store.get_unit("UOW-A01")
    assert u1_reloaded is not None
    transition_unit_state(u1_reloaded, UnitState.ACCEPTED, author=author, store=store)

    # Downstream workflow unblocks
    unblocked = runtime.refresh_workflow_states("WFL-B01", author=author)
    assert len(unblocked) == 1
    assert unblocked[0].id == "UOW-B01"
    assert unblocked[0].state == UnitState.READY

    # 3. Ingest external datasheet note with collision
    external_raw = (
        "---\n"
        "id: IDEA-A01\n"
        "type: idea\n"
        "title: External Optical Coating Idea\n"
        "domain: optics\n"
        "---\n"
        "Anti-reflective coatings."
    )
    imported = ingest_external_node(store=store, raw_text=external_raw, source_vault="lab-vault", author=author)
    assert imported.id == "IDEA-A02"
    assert imported.attrs.get("foreign_id") == "IDEA-A01"
    assert "vault:lab-vault" in imported.tags
