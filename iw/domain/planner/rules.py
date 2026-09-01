"""Maturation rules for generating ordered, sized activity steps."""

from iw.contracts.models import AuthorKind
from iw.contracts.planner import PlanStep


def _append_cml2_steps(steps: list[PlanStep], scores: dict[str, int], target_cml: int) -> None:
    if target_cml >= 2 and scores.get("novel", 1) < target_cml:
        steps.append(PlanStep(
            step_index=len(steps),
            title="Prior-Art & Patent Landscape Survey",
            activity_id="prior-art-survey@1",
            target_score="novel",
            assignee_kind=AuthorKind.AGENT,
            size="small",
            estimate_hours=1.0,
            depends_on=[],
            reason="Prior-art survey against the world before investing in deep design.",
        ))
    if target_cml >= 2 and scores.get("story", 1) < 2:
        steps.append(PlanStep(
            step_index=len(steps),
            title="DARPA Heilmeier Catechism Screening",
            activity_id="heilmeier-screening@1",
            target_score="story",
            assignee_kind=AuthorKind.AGENT,
            size="small",
            estimate_hours=1.0,
            depends_on=[],
            reason="Jargon-free objective framing and stakeholder impact assessment.",
        ))


def _append_cml3_steps(steps: list[PlanStep], target_cml: int) -> tuple[int | None, int | None]:
    if target_cml < 3:
        return None, None
    div_idx = len(steps)
    steps.append(PlanStep(
        step_index=div_idx,
        title="A-Team Divergent Architecture Generation",
        activity_id="divergent-generation@1",
        target_score="works",
        assignee_kind=AuthorKind.AGENT,
        size="medium",
        estimate_hours=1.5,
        depends_on=[],
        reason="Unfiltered candidate generation exploring distinct physical paradigms.",
    ))
    conv_idx = len(steps)
    steps.append(PlanStep(
        step_index=conv_idx,
        title="A-Team Convergent Architecture Screening",
        activity_id="convergent-screening@1",
        target_score="works",
        assignee_kind=AuthorKind.HUMAN,
        size="small",
        estimate_hours=1.0,
        depends_on=[div_idx],
        reason="Pre-declared criteria screening and rejected_because edge creation.",
    ))
    return div_idx, conv_idx


def _append_reach_and_trade_steps(steps: list[PlanStep], scores: dict[str, int], conv_idx: int | None) -> int:
    if scores.get("reach", 1) < 4:
        steps.append(PlanStep(
            step_index=len(steps),
            title="Parts & Skills Survey against Asset Portfolio",
            activity_id="parts-and-skills-survey@1",
            target_score="reach",
            assignee_kind=AuthorKind.AGENT,
            size="small",
            estimate_hours=1.0,
            depends_on=[],
            reason="Cross-reference requirements against AST-xxx portfolio and cost gap.",
        ))
    trade_idx = len(steps)
    trade_deps = [conv_idx] if conv_idx is not None else []
    steps.append(PlanStep(
        step_index=trade_idx,
        title="Architecture Trade Study & Sensitivity Pass",
        activity_id="trade-study@1",
        target_score="works",
        assignee_kind=AuthorKind.AGENT,
        size="medium",
        estimate_hours=1.5,
        depends_on=trade_deps,
        reason="Weighted scoring across criteria and weight sensitivity verification.",
    ))
    return trade_idx


def _append_point_design_and_story_steps(steps: list[PlanStep], scores: dict[str, int], trade_idx: int) -> None:
    steps.append(PlanStep(
        step_index=len(steps),
        title="Point Design & Subsystem Costing",
        activity_id="point-design@1",
        target_score="reach",
        assignee_kind=AuthorKind.AGENT,
        size="medium",
        estimate_hours=2.0,
        depends_on=[trade_idx],
        reason="Cost chosen concept in BOM parts, hours, money, and calendar schedule.",
    ))
    if scores.get("story", 1) < 4:
        steps.append(PlanStep(
            step_index=len(steps),
            title="One-Paragraph Narrative Story & Pitch",
            activity_id="story-draft@1",
            target_score="story",
            assignee_kind=AuthorKind.HUMAN,
            size="small",
            estimate_hours=1.0,
            depends_on=[],
            reason="PR-FAQ pitch for non-expert audience.",
        ))


def _append_cml4_steps(steps: list[PlanStep], scores: dict[str, int], target_cml: int, conv_idx: int | None) -> None:
    if target_cml < 4:
        return
    trade_idx = _append_reach_and_trade_steps(steps, scores, conv_idx)
    _append_point_design_and_story_steps(steps, scores, trade_idx)


def _append_cml5_steps(steps: list[PlanStep], target_cml: int) -> None:
    if target_cml < 5:
        return
    exp_idx = len(steps)
    steps.append(PlanStep(
        step_index=exp_idx,
        title="Decisive Experiment & Test Plan Design",
        activity_id="experiment-design@1",
        target_score="works",
        assignee_kind=AuthorKind.AGENT,
        size="small",
        estimate_hours=1.0,
        depends_on=[],
        reason="Falsifiable hypothesis, measurement protocol, and advance kill threshold.",
    ))
    steps.append(PlanStep(
        step_index=len(steps),
        title="Minimal Prototype Build & Measurement",
        activity_id="prototype-and-measure@1",
        target_score="works",
        assignee_kind=AuthorKind.HUMAN,
        size="medium",
        estimate_hours=2.0,
        depends_on=[exp_idx],
        reason="Physical proof of mechanism against advance kill criteria.",
    ))


def generate_maturation_steps(
    current_scores: dict[str, int],
    current_cml: int,
    target_cml: int,
) -> list[PlanStep]:
    """Generate ordered, dependency-linked steps to mature an idea to target CML."""
    target = min(5, max(current_cml + 1, target_cml))
    steps: list[PlanStep] = []
    _append_cml2_steps(steps, current_scores, target)
    _, conv_idx = _append_cml3_steps(steps, target)
    _append_cml4_steps(steps, current_scores, target, conv_idx)
    _append_cml5_steps(steps, target)
    return steps
