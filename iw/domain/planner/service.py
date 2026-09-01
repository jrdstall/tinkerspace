"""Planner domain service implementing maturation workflow generation."""

from datetime import datetime, timezone
from pathlib import Path
import yaml

from iw.contracts.models import Author, AuthorKind, Node, UnitOfWork, UnitState, Workflow
from iw.contracts.planner import ActivityCatalogItem, MaturationPlan, PlanStep
from iw.core.events import FileEventLog
from iw.core.ids import allocate_next_id
from iw.core.units import atomic_write_unit_yaml, scan_vault_units
from iw.core.workflows import atomic_write_workflow_yaml, scan_vault_workflows
from iw.domain.assessor.cml import compute_cml
from iw.domain.planner.rules import generate_maturation_steps


class PlannerService:
    """Drafts maturation plans and instantiates workflows."""

    def __init__(
        self,
        vault_dir: Path,
        templates_dir: Path | None = None,
        event_log: FileEventLog | None = None,
    ) -> None:
        self.vault_dir = vault_dir
        if templates_dir is not None:
            self.templates_dir = templates_dir
        else:
            self.templates_dir = Path(__file__).resolve().parent.parent.parent.parent / "content" / "templates"
        self.event_log = event_log

    def draft_plan(
        self,
        node: Node,
        target_cml: int,
        custom_focus: str | None = None,
    ) -> MaturationPlan:
        scores = dict(node.attrs.get("scores", {}))
        current_cml = compute_cml(scores)
        steps = generate_maturation_steps(scores, current_cml, target_cml)

        rationale = (
            f"Advancement plan from CML {current_cml} to CML {target_cml} for '{node.title}'. "
            f"Sequencing {len(steps)} activities prioritizing cheap, decisive validation first."
        )
        if custom_focus:
            rationale += f" Focus: {custom_focus}"

        return MaturationPlan(
            subject_id=node.id,
            current_cml=current_cml,
            target_cml=target_cml,
            current_scores=scores,
            steps=steps,
            rationale=rationale,
        )

    def list_activity_catalog(self) -> list[ActivityCatalogItem]:
        items: list[ActivityCatalogItem] = [
            ActivityCatalogItem(
                id="freeform@1",
                title="Freeform / Custom Task",
                category="custom",
                description="Open-ended task defined on the spot with custom instructions.",
                advances="varies",
            )
        ]
        if self.templates_dir.exists():
            for p in sorted(self.templates_dir.glob("*.yaml")):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if isinstance(data, dict) and "id" in data:
                        items.append(
                            ActivityCatalogItem(
                                id=data["id"],
                                title=data.get("title", data["id"]),
                                category=data.get("category", "general"),
                                description=data.get("description", "").strip(),
                                advances=data.get("advances", "works"),
                                target_output=data.get("target_output", "deliverable.md"),
                            )
                        )
                except Exception:
                    continue
        return items

    def build_custom_plan(
        self,
        subject_id: str,
        steps: list[PlanStep],
        target_cml: int = 5,
        rationale: str = "Custom human-authored maturation plan",
    ) -> MaturationPlan:
        reindexed_steps: list[PlanStep] = []
        for idx, s in enumerate(steps):
            reindexed_steps.append(
                PlanStep(
                    step_index=idx,
                    title=s.title,
                    activity_id=s.activity_id,
                    target_score=s.target_score,
                    assignee_kind=s.assignee_kind,
                    size=s.size,
                    estimate_hours=s.estimate_hours,
                    depends_on=[d for d in s.depends_on if d < idx],
                    reason=s.reason,
                )
            )
        return MaturationPlan(
            subject_id=subject_id,
            current_cml=1,
            target_cml=target_cml,
            current_scores={},
            steps=reindexed_steps,
            rationale=rationale,
        )

    def _allocate_ids(self, step_count: int) -> tuple[str, list[str]]:
        existing_wfls = scan_vault_workflows(self.vault_dir)
        wfl_id = allocate_next_id("WFL", [w.id for w in existing_wfls])
        existing_units = scan_vault_units(self.vault_dir)
        existing_uow_ids = [u.id for u in existing_units]
        uow_ids: list[str] = []
        for _ in range(step_count):
            new_uow_id = allocate_next_id("UOW", existing_uow_ids + uow_ids)
            uow_ids.append(new_uow_id)
        return wfl_id, uow_ids

    def _create_units(
        self,
        plan: MaturationPlan,
        wfl_id: str,
        uow_ids: list[str],
    ) -> tuple[dict[str, list[str]], list[UnitOfWork]]:
        dependencies: dict[str, list[str]] = {}
        units: list[UnitOfWork] = []
        for step in plan.steps:
            uow_id = uow_ids[step.step_index]
            dep_uow_ids = [uow_ids[d] for d in step.depends_on if d < len(uow_ids)]
            dependencies[uow_id] = dep_uow_ids
            initial_state = UnitState.BLOCKED if dep_uow_ids else UnitState.READY
            unit = UnitOfWork(
                id=uow_id,
                title=step.title,
                activity=step.activity_id.split("@")[0],
                state=initial_state,
                subject_ids=[plan.subject_id],
                workflow_id=wfl_id,
                assignee={"kind": step.assignee_kind.value},
                estimate={"my_time": f"{step.estimate_hours}h", "size": step.size},
                template=step.activity_id,
                action_guide=step.reason,
            )
            units.append(unit)
        return dependencies, units

    def instantiate_workflow(
        self,
        plan: MaturationPlan,
        author: Author,
    ) -> Workflow:
        wfl_id, uow_ids = self._allocate_ids(len(plan.steps))
        dependencies, units = self._create_units(plan, wfl_id, uow_ids)

        work_root = self.vault_dir / "work"
        for unit in units:
            unit_folder = work_root / unit.id
            atomic_write_unit_yaml(unit_folder, unit)

        workflow = Workflow(
            id=wfl_id,
            title=f"Maturation CML {plan.current_cml}->{plan.target_cml}: {plan.subject_id}",
            subject_ids=[plan.subject_id],
            unit_ids=uow_ids,
            dependencies=dependencies,
            workflow_dependencies=[],
            created=datetime.now(timezone.utc),
            template_id="maturation-plan@1",
        )
        wfl_folder = work_root / wfl_id
        atomic_write_workflow_yaml(wfl_folder, workflow)

        if self.event_log:
            self.event_log.append(
                kind="workflow.instantiated",
                subject_id=plan.subject_id,
                author=author,
                payload={"workflow_id": wfl_id, "unit_ids": uow_ids, "target_cml": plan.target_cml},
            )
        return workflow
