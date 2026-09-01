"""Behaviour tests for the Maturation Planner service.

Proves PLANNER-01 through PLANNER-10 from docs/design/specs/PLANNER.md:
- PLANNER-01: MaturationPlan generation
- PLANNER-02: Cheap and decisive sequencing
- PLANNER-03: Single-session step sizing
- PLANNER-04: DAG dependency structure
- PLANNER-05: Score laggard targeting
- PLANNER-06: Plan customization before execution
- PLANNER-07: Disk workflow and unit creation
- PLANNER-08: CML 5 empirical validation steps
- PLANNER-09: Activity catalog discovery
- PLANNER-10: Custom human-authored maturation plan
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from iw.contracts.models import Author, AuthorKind, Node, UnitState
from iw.contracts.planner import MaturationPlan, PlanStep
from iw.core.events import FileEventLog
from iw.core.units import read_unit_yaml
from iw.core.workflows import read_workflow_yaml
from iw.domain.planner.service import PlannerService


def make_test_idea(id: str = "IDEA-A01", scores: dict[str, int] | None = None) -> Node:
    return Node(
        id=id,
        type="idea",
        title="Piezoelectric Bicycle Fork Energy Harvester",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["energy", "cycling"],
        attrs={"scores": scores or {}},
    )


def test_planner_01_draft_plan_creates_maturation_plan(tmp_path: Path):
    """PLANNER-01: Planner generates a MaturationPlan for a given idea and target CML."""
    planner = PlannerService(tmp_path)
    idea = make_test_idea(scores={"novel": 1, "works": 1, "reach": 1, "story": 1})

    plan = planner.draft_plan(idea, target_cml=3)
    assert plan.subject_id == "IDEA-A01"
    assert plan.current_cml == 1
    assert plan.target_cml == 3
    assert len(plan.steps) >= 3


def test_planner_02_sequencing_cheap_and_decisive_first(tmp_path: Path):
    """PLANNER-02: Cheap and decisive activities precede expensive or committed engineering."""
    planner = PlannerService(tmp_path)
    idea = make_test_idea(scores={"novel": 1, "works": 1, "reach": 1, "story": 1})
    plan = planner.draft_plan(idea, target_cml=4)

    activities = [s.activity_id for s in plan.steps]
    assert activities.index("prior-art-survey@1") < activities.index("trade-study@1")
    assert activities.index("convergent-screening@1") < activities.index("trade-study@1")
    assert activities.index("trade-study@1") < activities.index("point-design@1")


def test_planner_03_steps_are_sized_to_free_time_blocks(tmp_path: Path):
    """PLANNER-03: Every step is sized for 1-2 hour sessions."""
    planner = PlannerService(tmp_path)
    idea = make_test_idea(scores={"novel": 2, "works": 2, "reach": 2, "story": 2})
    plan = planner.draft_plan(idea, target_cml=5)

    for step in plan.steps:
        assert step.estimate_hours <= 2.0
        assert step.size in ("small", "medium")


def test_planner_04_steps_declare_dag_dependencies(tmp_path: Path):
    """PLANNER-04: Step dependencies form a valid DAG with non-cyclical upstream references."""
    planner = PlannerService(tmp_path)
    idea = make_test_idea(scores={"novel": 1, "works": 1, "reach": 1, "story": 1})
    plan = planner.draft_plan(idea, target_cml=4)

    for step in plan.steps:
        for dep_idx in step.depends_on:
            assert dep_idx < step.step_index


def test_planner_05_targets_identified_score_laggards(tmp_path: Path):
    """PLANNER-05: Specific laggards receive targeted advancement activities."""
    planner = PlannerService(tmp_path)
    idea = make_test_idea(scores={"novel": 1, "works": 3, "reach": 3, "story": 3})
    plan = planner.draft_plan(idea, target_cml=3)

    target_scores = [s.target_score for s in plan.steps]
    assert "novel" in target_scores


def test_planner_06_plan_can_be_customized_before_instantiation(tmp_path: Path):
    """PLANNER-06: Drafted plan can be customized before being instantiated into a workflow."""
    planner = PlannerService(tmp_path)
    idea = make_test_idea(scores={"novel": 2, "works": 2, "reach": 2, "story": 2})
    plan = planner.draft_plan(idea, target_cml=3)

    custom_step = PlanStep(
        step_index=len(plan.steps),
        title="Custom Lab Vibration Rig Test",
        activity_id="experiment-design@1",
        target_score="works",
        assignee_kind=AuthorKind.HUMAN,
        size="small",
        estimate_hours=1.0,
        depends_on=[],
        reason="Custom empirical verification",
    )
    customized_plan = MaturationPlan(
        subject_id=plan.subject_id,
        current_cml=plan.current_cml,
        target_cml=plan.target_cml,
        current_scores=plan.current_scores,
        steps=plan.steps + [custom_step],
        rationale="Customized plan",
    )

    author = Author(kind=AuthorKind.HUMAN, courier="test")
    workflow = planner.instantiate_workflow(customized_plan, author=author)
    assert len(workflow.unit_ids) == len(customized_plan.steps)


def test_planner_07_instantiate_workflow_creates_wfl_and_uow_files_on_disk(tmp_path: Path):
    """PLANNER-07: Instantiation creates valid WFL and UOW files on disk."""
    event_log = FileEventLog(tmp_path / "events.jsonl")
    planner = PlannerService(tmp_path, event_log=event_log)
    idea = make_test_idea(scores={"novel": 1, "works": 1, "reach": 1, "story": 1})
    plan = planner.draft_plan(idea, target_cml=3)

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    wfl = planner.instantiate_workflow(plan, author=author)

    assert wfl.id.startswith("WFL-")
    wfl_file = tmp_path / "work" / wfl.id / "workflow.yaml"
    loaded_wfl = read_workflow_yaml(wfl_file)
    assert loaded_wfl is not None
    assert loaded_wfl.id == wfl.id

    first_uow = read_unit_yaml(tmp_path / "work" / wfl.unit_ids[0] / "unit.yaml")
    assert first_uow is not None
    assert first_uow.state == UnitState.READY


def test_planner_08_cml5_target_includes_experiment_and_prototype_steps(tmp_path: Path):
    """PLANNER-08: Target CML 5 mandates experiment design and prototype measurement."""
    planner = PlannerService(tmp_path)
    idea = make_test_idea(scores={"novel": 4, "works": 4, "reach": 4, "story": 4})
    plan = planner.draft_plan(idea, target_cml=5)

    activities = [s.activity_id for s in plan.steps]
    assert "experiment-design@1" in activities
    assert "prototype-and-measure@1" in activities


def test_planner_09_catalog_discovery_lists_available_activities(tmp_path: Path):
    """PLANNER-09: Activity catalog discovery returns all available templates and freeform."""
    planner = PlannerService(tmp_path)
    catalog = planner.list_activity_catalog()

    assert len(catalog) >= 10
    catalog_ids = [item.id for item in catalog]
    assert "freeform@1" in catalog_ids
    assert "divergent-generation@1" in catalog_ids
    assert "trade-study@1" in catalog_ids


def test_planner_10_custom_plan_construction_and_instantiation(tmp_path: Path):
    """PLANNER-10: Custom human-authored plan can be assembled and instantiated."""
    planner = PlannerService(tmp_path)

    steps = [
        PlanStep(
            step_index=0,
            title="Examine existing patents on piezo cantilever beams",
            activity_id="prior-art-survey@1",
            target_score="novel",
            assignee_kind=AuthorKind.AGENT,
            size="small",
            estimate_hours=1.0,
            depends_on=[],
            reason="Establish novel differentiator",
        ),
        PlanStep(
            step_index=1,
            title="CAD block model of fork mount bracket in Fusion 360",
            activity_id="freeform@1",
            target_score="works",
            assignee_kind=AuthorKind.HUMAN,
            size="medium",
            estimate_hours=1.5,
            depends_on=[0],
            reason="Freeform mechanical design step",
        ),
    ]

    custom_plan = planner.build_custom_plan(
        subject_id="IDEA-A01",
        steps=steps,
        target_cml=3,
        rationale="Jared's hand-crafted piezo fork maturation workflow",
    )

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    wfl = planner.instantiate_workflow(custom_plan, author=author)

    assert len(wfl.unit_ids) == 2
    uow1 = read_unit_yaml(tmp_path / "work" / wfl.unit_ids[0] / "unit.yaml")
    uow2 = read_unit_yaml(tmp_path / "work" / wfl.unit_ids[1] / "unit.yaml")

    assert uow1.state == UnitState.READY
    assert uow2.state == UnitState.BLOCKED
    assert wfl.dependencies[uow2.id] == [uow1.id]
