"""Behaviour tests for Workflow Diagram web view.

Traces WFLVIEW-01 through WFLVIEW-04 per docs/design/specs/WFLVIEW.md.
"""

from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, UnitOfWork, UnitState, Workflow
from iw.core.store import MarkdownStore
from iw.domain.workflow.runtime import WorkflowRuntime
from iw.web.app import create_app


def _setup_test_workflow(tmp_path: Path) -> tuple[MarkdownStore, WorkflowRuntime, Workflow]:
    store = MarkdownStore(vault_dir=tmp_path)
    runtime = WorkflowRuntime(store=store, vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    wfl = Workflow(
        id="WFL-A01",
        title="Handlebar Display Maturation Workflow",
        subject_ids=["IDEA-A01"],
        unit_ids=["UOW-A01", "UOW-A02", "UOW-A03"],
        dependencies={"UOW-A02": ["UOW-A01"], "UOW-A03": ["UOW-A02"]},
    )
    units = [
        UnitOfWork(
            id="UOW-A01",
            title="Step 1: Prior Art Survey",
            activity="prior-art-survey@1",
            state=UnitState.READY,
            subject_ids=["IDEA-A01"],
            action_guide="1. ASSIGNEE: Agent\n2. TASK: Search existing patents\n5. RESUME: Call submit_result",
        ),
        UnitOfWork(
            id="UOW-A02",
            title="Step 2: Technical Feasibility",
            activity="trade-study@1",
            state=UnitState.BLOCKED,
            subject_ids=["IDEA-A01"],
        ),
        UnitOfWork(
            id="UOW-A03",
            title="Step 3: Screening Assessment",
            activity="screening-assessment@1",
            state=UnitState.BLOCKED,
            subject_ids=["IDEA-A01"],
        ),
    ]
    runtime.create_workflow(wfl, units, author=author)
    return store, runtime, wfl


def test_wflview_01_renders_workflow_dag_diagram(tmp_path: Path):
    """WFLVIEW-01: The Workflow View renders a visual dependency DAG diagram of all units."""
    store, runtime, wfl = _setup_test_workflow(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/workflow/WFL-A01")
    assert response.status_code == 200
    html = response.text

    assert "Handlebar Display Maturation Workflow" in html
    assert "WFL-A01" in html
    assert "UOW-A01" in html
    assert "Step 1: Prior Art Survey" in html
    assert "UOW-A02" in html
    assert "Step 2: Technical Feasibility" in html
    assert "UOW-A03" in html
    assert "Step 3: Screening Assessment" in html


def test_wflview_02_step_nodes_display_status_color_coding(tmp_path: Path):
    """WFLVIEW-02: Step nodes display explicit lifecycle status color-coding and badges."""
    store, runtime, wfl = _setup_test_workflow(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/workflow/WFL-A01")
    assert response.status_code == 200
    html = response.text

    assert "Ready" in html
    assert "Blocked" in html
    assert "Waiting on Upstream" in html


def test_wflview_03_renders_predecessor_dependency_connectors(tmp_path: Path):
    """WFLVIEW-03: Step nodes render dependency connectors showing predecessor-to-successor execution flow."""
    store, runtime, wfl = _setup_test_workflow(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/workflow/WFL-A01")
    assert response.status_code == 200
    html = response.text

    assert "Root Step" in html
    assert "Depends on: <strong>UOW-A01</strong>" in html
    assert "Next: <strong>UOW-A02</strong>" in html
    assert "Depends on: <strong>UOW-A02</strong>" in html


def test_wflview_04_step_action_controls_and_subject_links(tmp_path: Path):
    """WFLVIEW-04: Each step node provides action controls and links to subject nodes."""
    store, runtime, wfl = _setup_test_workflow(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/workflow/WFL-A01")
    assert response.status_code == 200
    html = response.text

    # Subject node links
    assert 'href="/node/IDEA-A01"' in html
    # Action guide banner
    assert "📋 ACTION GUIDE" in html
    assert "Search existing patents" in html
    # Action buttons for ready step
    assert "🚀 Dispatch" in html
    assert "⏸️ Park" in html
    assert "⏭️ Skip" in html
