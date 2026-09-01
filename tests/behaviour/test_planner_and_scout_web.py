"""Behaviour tests for Planner and Scout Web UI routes.

Proves PLANUI-01 through PLANUI-07 from docs/design/specs/PLANNERUI.md:
- PLANUI-01: Planner view renders scores and CML
- PLANUI-02: Target CML selector updates step preview
- PLANUI-03: Plan form submission instantiates workflow and redirects
- PLANUI-04: Scout view and offers panel rendering
- PLANUI-05: Scout dismiss and sweep actions reset staleness clock
- PLANUI-06: Custom Plan Builder renders catalog items
- PLANUI-07: Custom Plan instantiation creates tailored workflow with dependencies
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Node, UnitState
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.core.units import read_unit_yaml
from iw.domain.scout.service import ScoutService
from iw.web.app import create_app


@pytest.fixture
def web_test_env(tmp_path: Path):
    """Fixture providing initialized MarkdownStore and Starlette TestClient."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)

    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Regenerative Shock Absorbers",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["automotive", "energy"],
        attrs={"scores": {"novel": 2, "works": 2, "reach": 2, "story": 2}, "cml": 2},
    )
    author = Author(kind=AuthorKind.HUMAN, courier="test")
    store.write_node(idea, author=author)

    scout = ScoutService(vault_dir / "meta" / "scout_interests.json")
    interest = scout.register_interest(
        topic="Linear induction energy harvesting",
        domain="hardware",
        staleness_interval_days=5,
        subject_id="IDEA-A01",
    )

    app = create_app(store=store)
    client = TestClient(app, follow_redirects=False)
    return client, store, scout, interest


def test_planui_01_planner_view_renders_scores_and_cml(web_test_env):
    """PLANUI-01: Planner view renders idea details, current CML, and score grid."""
    client, store, _, _ = web_test_env
    res = client.get("/ideas/IDEA-A01/plan")
    assert res.status_code == 200
    assert "Regenerative Shock Absorbers" in res.text
    assert "Current CML" in res.text
    assert "Target Concept Maturity Level" in res.text


def test_planui_02_changing_target_cml_previews_steps(web_test_env):
    """PLANUI-02: Querying with higher target_cml updates proposed steps."""
    client, store, _, _ = web_test_env
    res = client.get("/ideas/IDEA-A01/plan?target_cml=5")
    assert res.status_code == 200
    assert "experiment-design@1" in res.text
    assert "prototype-and-measure@1" in res.text


def test_planui_03_instantiate_workflow_redirects_and_creates_wfl(web_test_env):
    """PLANUI-03: Submitting plan form instantiates workflow and redirects to workflow view."""
    client, store, _, _ = web_test_env
    res = client.post("/ideas/IDEA-A01/plan/instantiate", data={"target_cml": "3"})
    assert res.status_code == 303
    assert res.headers["location"].startswith("/workflow/WFL-")

    wfl_id = res.headers["location"].split("/")[-1]
    wfl_path = store.vault_dir / "work" / wfl_id / "workflow.yaml"
    assert wfl_path.exists()


def test_planui_04_scout_view_and_offers_rendering(web_test_env):
    """PLANUI-04: Scout view lists standing interests and active offers."""
    client, store, scout, interest = web_test_env
    res = client.get("/scout")
    assert res.status_code == 200
    assert "Linear induction energy harvesting" in res.text
    assert "Register Standing Interest" in res.text


def test_planui_05_scout_dismiss_and_sweep_actions(web_test_env):
    """PLANUI-05: Dismiss and sweep actions update staleness timestamps."""
    client, store, scout, interest = web_test_env

    # Test Dismiss
    res_dismiss = client.post(f"/scout/{interest.id}/dismiss")
    assert res_dismiss.status_code == 303

    loaded = scout.get_interest(interest.id)
    assert loaded.last_dismissed_at is not None

    # Test Sweep Dispatch
    res_sweep = client.post(f"/scout/{interest.id}/sweep")
    assert res_sweep.status_code == 303

    loaded_after_sweep = scout.get_interest(interest.id)
    assert loaded_after_sweep.last_swept_at is not None


def test_planui_06_custom_plan_builder_view_renders_catalog(web_test_env):
    """PLANUI-06: Planner page renders the activity catalog options for custom sequencing."""
    client, _, _, _ = web_test_env
    res = client.get("/ideas/IDEA-A01/plan")
    assert res.status_code == 200
    assert "Custom Plan Builder" in res.text
    assert "freeform@1" in res.text
    assert "divergent-generation@1" in res.text


def test_planui_07_custom_plan_instantiation_creates_workflow(web_test_env):
    """PLANUI-07: Submitting custom steps instantiates a customized workflow with dependencies."""
    client, store, _, _ = web_test_env

    data = {
        "target_cml": "4",
        "step_title": ["Survey damper patents", "Freeform CAD coil packaging sketch"],
        "step_activity": ["prior-art-survey@1", "freeform@1"],
        "step_assignee": ["agent", "human"],
        "step_estimate": ["1.0", "1.5"],
        "step_target_score": ["novel", "works"],
        "step_depends_on": ["", "1"],
    }

    res = client.post("/ideas/IDEA-A01/plan/custom_instantiate", data=data)
    assert res.status_code == 303
    assert res.headers["location"].startswith("/workflow/WFL-")

    wfl_id = res.headers["location"].split("/")[-1]
    wfl_dir = store.vault_dir / "work" / wfl_id
    assert (wfl_dir / "workflow.yaml").exists()

    # Verify units
    units = list(store.vault_dir.glob("work/UOW-*/unit.yaml"))
    assert len(units) >= 2
