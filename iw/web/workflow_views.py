"""Workflow Diagram web view handlers.

Serves the visual DAG workflow diagram view (/workflow/{workflow_id}) per TS-04.
"""

from typing import Any
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.templating import Jinja2Templates

from iw.contracts.models import Author, AuthorKind, UnitOfWork, Workflow
from iw.contracts.store import StoreProtocol
from iw.domain.workflow.runtime import WorkflowRuntime


def _build_step_views(workflow: Workflow, store: StoreProtocol) -> list[dict[str, Any]]:
    """Build enriched step node structures for DAG rendering."""
    steps: list[dict[str, Any]] = []
    for uid in workflow.unit_ids:
        unit = store.get_unit(uid)
        preds = workflow.dependencies.get(uid.upper(), [])
        succs: list[str] = []
        for other_uid, other_preds in workflow.dependencies.items():
            if uid.upper() in [p.upper() for p in other_preds]:
                succs.append(other_uid.upper())

        steps.append({
            "id": uid.upper(),
            "unit": unit,
            "title": unit.title if unit else uid,
            "state": unit.state.value if unit else "unknown",
            "activity": unit.activity if unit else "",
            "action_guide": unit.action_guide if unit else "",
            "subject_ids": unit.subject_ids if unit else workflow.subject_ids,
            "predecessors": preds,
            "successors": succs,
        })
    return steps


async def workflow_view(request: Request, templates: Jinja2Templates) -> Response:
    """Render the Workflow DAG Diagram view."""
    store: StoreProtocol = request.app.state.store
    vault_dir = getattr(store, "vault_dir", None)
    runtime = WorkflowRuntime(store=store, vault_dir=vault_dir) if vault_dir else None

    workflow_id = request.path_params.get("workflow_id", "").strip().upper()
    workflow = runtime.get_workflow(workflow_id) if runtime else None
    if not workflow:
        return HTMLResponse(f"<h1>404 Not Found</h1><p>Workflow '{workflow_id}' does not exist.</p>", status_code=404)

    # Refresh states before rendering
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    if runtime:
        runtime.refresh_workflow_states(workflow.id, author=author)

    steps = _build_step_views(workflow, store)

    return templates.TemplateResponse(
        request=request,
        name="workflow.html",
        context={
            "request": request,
            "workflow": workflow,
            "steps": steps,
            "inbox_count": len(store.list_inbox()),
            "drop_count": len(store.list_dropped_files()),
        },
    )
