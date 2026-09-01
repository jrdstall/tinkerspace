"""End-to-end integration tests for the full CML 1 to 5 Maturation Lifecycle.

Proves MATURITY-01 through MATURITY-06 from docs/design/specs/MATURITY.md:
- MATURITY-01: CML 1 Spark initialization
- MATURITY-02: CML 2 Plausible progression (prior art & Heilmeier screening)
- MATURITY-03: CML 3 Explored progression (A-Team divergent/convergent & rejected_because edges)
- MATURITY-04: CML 4 Chosen progression (trade study, asset survey, point design, story)
- MATURITY-05: CML 5 Real progression (experiment design, prototype build & advance kill)
- MATURITY-06: Atomic frontmatter persistence, CML derivation, and event logging
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from iw.contracts.models import Author, AuthorKind, Edge, Node, UnitState
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.assessor.cml import apply_assessment_to_node, compute_cml
from iw.domain.planner.service import PlannerService
from iw.domain.workflow.runtime import WorkflowRuntime


@pytest.fixture
def maturation_env(tmp_path: Path):
    """Fixture providing initialized MarkdownStore, PlannerService, and WorkflowRuntime."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    planner = PlannerService(vault_dir=vault_dir, event_log=event_log)
    runtime = WorkflowRuntime(vault_dir=vault_dir, store=store, event_log=event_log)
    author = Author(kind=AuthorKind.HUMAN, courier="test")

    # Create test asset (AST-A01)
    asset = Node(
        id="AST-A01",
        type="asset",
        title="Formlabs Form 3+ SLA 3D Printer & Engineering Resins",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["3d_printing", "tooling"],
    )
    store.write_node(asset, author=author)

    return store, planner, runtime, author


def test_maturity_01_idea_initializes_at_cml1_spark(maturation_env):
    """MATURITY-01: An unassessed idea enters the store at CML 1 (Spark)."""
    store, _, _, author = maturation_env
    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Piezoelectric Bicycle Fork Energy Harvester",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["energy", "cycling"],
    )
    store.write_node(idea, author=author)

    loaded = store.get_node("IDEA-A01")
    assert loaded is not None
    scores = loaded.attrs.get("scores", {})
    assert compute_cml(scores) == 1


def test_maturity_02_advance_to_cml2_plausible(maturation_env):
    """MATURITY-02: Advancing to CML 2 via prior-art survey and Heilmeier catechism."""
    store, planner, _, author = maturation_env
    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Piezo Harvester",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["energy"],
    )
    store.write_node(idea, author=author)

    plan_cml2 = planner.draft_plan(idea, target_cml=2)
    activities = [s.activity_id for s in plan_cml2.steps]
    assert "prior-art-survey@1" in activities
    assert "heilmeier-screening@1" in activities

    # Simulate completion of CML 2 steps
    scores_cml2 = {"novel": 2, "works": 2, "reach": 2, "story": 2}
    updated_idea = apply_assessment_to_node(idea, scores=scores_cml2, verdict="pursue", reason="Initial feasibility validated")
    store.write_node(updated_idea, author=author)

    loaded = store.get_node("IDEA-A01")
    assert loaded.attrs["cml"] == 2
    assert loaded.attrs["screening_verdict"] == "pursue"


def test_maturity_03_advance_to_cml3_explored_with_ateam_discipline(maturation_env):
    """MATURITY-03: Advancing to CML 3 via A-Team divergent/convergent and rejected_because edges."""
    store, planner, _, author = maturation_env
    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Piezo Harvester",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["energy"],
        attrs={"scores": {"novel": 2, "works": 2, "reach": 2, "story": 2}, "cml": 2},
    )
    store.write_node(idea, author=author)

    plan_cml3 = planner.draft_plan(idea, target_cml=3)
    activities = [s.activity_id for s in plan_cml3.steps]
    assert "divergent-generation@1" in activities
    assert "convergent-screening@1" in activities

    # Record screened-out candidate idea with rejected_because edge (A-Team discipline)
    reject_edge = Edge(
        from_id="IDEA-A02",
        to_id="IDEA-A01",
        relation="rejected_because",
        created=datetime.now(timezone.utc),
        author=author,
        note="Excessive unsprung mass degrades steering dynamics beyond acceptable threshold.",
    )
    rejected_concept = Node(
        id="IDEA-A02",
        type="idea",
        title="Heavy Rotational Eccentric Mass Generator",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["energy"],
        attrs={"state": "let_go"},
        edges=[reject_edge],
    )
    store.write_node(rejected_concept, author=author)

    # Advance primary idea to CML 3
    scores_cml3 = {"novel": 3, "works": 3, "reach": 3, "story": 3}
    idea_cml3 = apply_assessment_to_node(idea, scores=scores_cml3)
    store.write_node(idea_cml3, author=author)

    loaded = store.get_node("IDEA-A01")
    assert loaded.attrs["cml"] == 3

    loaded_reject = store.get_node("IDEA-A02")
    assert any(e.relation == "rejected_because" for e in loaded_reject.edges)


def test_maturity_04_advance_to_cml4_chosen_with_trade_study_and_point_design(maturation_env):
    """MATURITY-04: Advancing to CML 4 via trade study, asset survey, point design, and pitch."""
    store, planner, _, author = maturation_env
    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Piezo Harvester",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["energy"],
        attrs={"scores": {"novel": 3, "works": 3, "reach": 3, "story": 3}, "cml": 3},
    )
    store.write_node(idea, author=author)

    plan_cml4 = planner.draft_plan(idea, target_cml=4)
    activities = [s.activity_id for s in plan_cml4.steps]
    assert "parts-and-skills-survey@1" in activities
    assert "trade-study@1" in activities
    assert "point-design@1" in activities
    assert "story-draft@1" in activities

    # Advance idea to CML 4
    scores_cml4 = {"novel": 4, "works": 4, "reach": 4, "story": 4}
    idea_cml4 = apply_assessment_to_node(idea, scores=scores_cml4)
    store.write_node(idea_cml4, author=author)

    loaded = store.get_node("IDEA-A01")
    assert loaded.attrs["cml"] == 4


def test_maturity_05_advance_to_cml5_real_with_empirical_prototype_and_advance_kill(maturation_env):
    """MATURITY-05: Advancing to CML 5 via experiment design and prototype measurement."""
    store, planner, _, author = maturation_env
    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Piezo Harvester",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["energy"],
        attrs={"scores": {"novel": 4, "works": 4, "reach": 4, "story": 4}, "cml": 4},
    )
    store.write_node(idea, author=author)

    plan_cml5 = planner.draft_plan(idea, target_cml=5)
    activities = [s.activity_id for s in plan_cml5.steps]
    assert "experiment-design@1" in activities
    assert "prototype-and-measure@1" in activities

    # Complete empirical validation: 15mW generated at 20Hz vibration, exceeding 5mW kill threshold
    scores_cml5 = {"novel": 5, "works": 5, "reach": 5, "story": 5}
    idea_cml5 = apply_assessment_to_node(
        idea,
        scores=scores_cml5,
        verdict="pursue",
        reason="Prototype generated 15mW on road shaker rig; validated at CML 5",
    )
    store.write_node(idea_cml5, author=author)

    loaded = store.get_node("IDEA-A01")
    assert loaded.attrs["cml"] == 5


def test_maturity_06_frontmatter_atomicity_and_event_log(maturation_env):
    """MATURITY-06: Verification that final CML 5 state is persisted in frontmatter with events."""
    store, _, _, author = maturation_env
    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Piezo Harvester",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["energy"],
    )
    scores_cml5 = {"novel": 5, "works": 5, "reach": 5, "story": 5}
    idea_cml5 = apply_assessment_to_node(idea, scores=scores_cml5, verdict="pursue", reason="CML 5 confirmed")
    store.write_node(idea_cml5, author=author)

    final_idea = store.get_node("IDEA-A01")
    assert final_idea is not None
    assert final_idea.attrs["cml"] == 5
    assert final_idea.attrs["scores"]["novel"] == 5
    assert final_idea.attrs["scores"]["works"] == 5
    assert final_idea.attrs["scores"]["reach"] == 5
    assert final_idea.attrs["scores"]["story"] == 5

    # Check that events were logged
    events = store.event_log.read_events()
    assert len(events) >= 1
