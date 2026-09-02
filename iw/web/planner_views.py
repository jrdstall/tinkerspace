"""Web route handlers for the Maturation Planner."""

from pathlib import Path
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.templating import Jinja2Templates

from iw.contracts.models import Author, AuthorKind
from iw.contracts.planner import PlanStep
from iw.contracts.store import StoreProtocol
from iw.domain.assessor.cml import compute_cml, identify_laggards
from iw.domain.planner.service import PlannerService


def _get_planner(request: Request) -> PlannerService:
    store: StoreProtocol = request.app.state.store
    vault_dir = store.vault_dir
    event_log = getattr(store, "event_log", None)
    return PlannerService(vault_dir=vault_dir, event_log=event_log)


async def planner_view(request: Request, templates: Jinja2Templates) -> Response:
    """Render the interactive Maturation Planner page for an idea."""
    store: StoreProtocol = request.app.state.store
    idea_id = request.path_params.get("idea_id", "").strip().upper()
    node = store.get_node(idea_id)
    if node is None or node.type != "idea":
        return HTMLResponse(f"<h1>404 Not Found</h1><p>Idea '{idea_id}' not found.</p>", status_code=404)

    planner = _get_planner(request)
    raw_target = request.query_params.get("target_cml", "")
    scores = dict(node.attrs.get("scores", {}))
    current_cml = compute_cml(scores)
    target_cml = int(raw_target) if raw_target.isdigit() else min(5, current_cml + 1)
    target_cml = max(current_cml + 1, min(5, target_cml))

    plan = planner.draft_plan(node, target_cml=target_cml)
    catalog = planner.list_activity_catalog()
    laggards = identify_laggards(scores)

    return templates.TemplateResponse(
        request=request,
        name="planner.html",
        context={
            "request": request,
            "node": node,
            "current_cml": current_cml,
            "target_cml": target_cml,
            "scores": scores,
            "laggards": laggards,
            "plan": plan,
            "catalog": catalog,
        },
    )


async def planner_instantiate_action(request: Request) -> Response:
    """Instantiate the drafted maturation plan into a concrete workflow."""
    store: StoreProtocol = request.app.state.store
    idea_id = request.path_params.get("idea_id", "").strip().upper()
    node = store.get_node(idea_id)
    if node is None:
        return HTMLResponse(f"<h1>404 Not Found</h1><p>Idea '{idea_id}' not found.</p>", status_code=404)

    form = await request.form()
    raw_target = str(form.get("target_cml", "2"))
    target_cml = int(raw_target) if raw_target.isdigit() else 2

    planner = _get_planner(request)
    plan = planner.draft_plan(node, target_cml=target_cml)

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    wfl = planner.instantiate_workflow(plan, author=author)

    return RedirectResponse(url=f"/workflow/{wfl.id}", status_code=303)


def _parse_step_deps(raw: str, max_idx: int) -> list[int]:
    deps: list[int] = []
    for d in str(raw).split(","):
        if d.strip().isdigit():
            val = int(d.strip()) - 1
            if 0 <= val < max_idx:
                deps.append(val)
    return deps


def _parse_custom_steps(form: dict) -> list[PlanStep]:
    titles = form.getlist("step_title") if hasattr(form, "getlist") else []
    activities = form.getlist("step_activity") if hasattr(form, "getlist") else []
    assignees = form.getlist("step_assignee") if hasattr(form, "getlist") else []
    estimates = form.getlist("step_estimate") if hasattr(form, "getlist") else []
    targets = form.getlist("step_target_score") if hasattr(form, "getlist") else []
    deps_raw = form.getlist("step_depends_on") if hasattr(form, "getlist") else []
    instructions = form.getlist("step_instructions") if hasattr(form, "getlist") else []

    steps: list[PlanStep] = []
    for idx, title in enumerate(titles):
        if not title.strip():
            continue
        act = activities[idx] if idx < len(activities) else "freeform@1"
        ass_str = assignees[idx] if idx < len(assignees) else "agent"
        ass_kind = AuthorKind.HUMAN if ass_str == "human" else AuthorKind.AGENT
        est_val = float(estimates[idx]) if idx < len(estimates) and estimates[idx] else 1.0
        tgt = targets[idx] if idx < len(targets) else "works"
        custom_inst = instructions[idx].strip() if idx < len(instructions) and instructions[idx].strip() else "Custom human-authored step"
        dep_raw = deps_raw[idx] if idx < len(deps_raw) else ""

        steps.append(
            PlanStep(
                step_index=idx, title=title.strip(), activity_id=act,
                target_score=tgt, assignee_kind=ass_kind,
                size="medium" if est_val > 1.0 else "small", estimate_hours=est_val,
                depends_on=_parse_step_deps(dep_raw, idx), reason=custom_inst,
            )
        )
    return steps


async def planner_custom_instantiate_action(request: Request) -> Response:
    """Instantiate a user-authored custom maturation plan."""
    store: StoreProtocol = request.app.state.store
    idea_id = request.path_params.get("idea_id", "").strip().upper()
    node = store.get_node(idea_id)
    if node is None:
        return HTMLResponse(f"<h1>404 Not Found</h1><p>Idea '{idea_id}' not found.</p>", status_code=404)

    form = await request.form()
    steps = _parse_custom_steps(form)
    if not steps:
        return RedirectResponse(url=f"/ideas/{idea_id}/plan", status_code=303)

    raw_target = str(form.get("target_cml", "5"))
    target_cml = int(raw_target) if raw_target.isdigit() else 5

    planner = _get_planner(request)
    plan = planner.build_custom_plan(idea_id, steps=steps, target_cml=target_cml)

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    wfl = planner.instantiate_workflow(plan, author=author)

    return RedirectResponse(url=f"/workflow/{wfl.id}", status_code=303)
