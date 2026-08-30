"""Work Board web view handlers.

Serves the central Work Board UI (/board), displays units by lifecycle state, and handles dispatch, park, skip, reset, and refresh actions.
"""

from typing import Any
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.templating import Jinja2Templates

from iw.contracts.models import Author, AuthorKind, UnitOfWork, UnitState
from iw.contracts.store import StoreProtocol
from iw.domain.workflow.runtime import WorkflowRuntime
from iw.domain.workflow.state import transition_unit_state


def _group_units_by_state(all_units: list[UnitOfWork]) -> dict[str, list[UnitOfWork]]:
    """Partition units into lifecycle buckets."""
    buckets: dict[str, list[UnitOfWork]] = {
        "ready": [],
        "dispatched": [],
        "returned": [],
        "parked": [],
    }
    for u in all_units:
        if u.state == UnitState.READY:
            buckets["ready"].append(u)
        elif u.state == UnitState.DISPATCHED:
            buckets["dispatched"].append(u)
        elif u.state == UnitState.RETURNED:
            buckets["returned"].append(u)
        elif u.state == UnitState.PARKED:
            buckets["parked"].append(u)
    return buckets


async def board_view(request: Request, templates: Jinja2Templates) -> Response:
    """Render the Work Board displaying units grouped by lifecycle state."""
    store: StoreProtocol = request.app.state.store
    vault_dir = getattr(store, "vault_dir", None)
    runtime = WorkflowRuntime(store=store, vault_dir=vault_dir) if vault_dir else None

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    if runtime:
        for wfl in runtime.list_workflows():
            runtime.refresh_workflow_states(wfl.id, author=author)

    b = _group_units_by_state(store.list_units())
    total_active = len(b["ready"]) + len(b["dispatched"]) + len(b["returned"])

    return templates.TemplateResponse(
        request=request,
        name="board.html",
        context={
            "request": request,
            "ready_units": b["ready"],
            "dispatched_units": b["dispatched"],
            "returned_units": b["returned"],
            "parked_units": b["parked"],
            "total_active": total_active,
            "inbox_count": len(store.list_inbox()),
            "drop_count": len(store.list_dropped_files()),
        },
    )


async def board_dispatch_view(request: Request) -> Response:
    """Handle dispatch action for a ready unit."""
    store: StoreProtocol = request.app.state.store
    form_data = await request.form()
    unit_id = str(form_data.get("unit_id", "")).strip().upper()

    unit = store.get_unit(unit_id)
    if unit and unit.state == UnitState.READY:
        author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
        transition_unit_state(unit, UnitState.DISPATCHED, author=author, store=store)

    return RedirectResponse(url="/board", status_code=303)


async def board_park_view(request: Request) -> Response:
    """Handle parking action for an active or ready unit."""
    store: StoreProtocol = request.app.state.store
    form_data = await request.form()
    unit_id = str(form_data.get("unit_id", "")).strip().upper()

    unit = store.get_unit(unit_id)
    if unit and unit.state in (UnitState.BLOCKED, UnitState.READY, UnitState.DISPATCHED, UnitState.RETURNED):
        author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
        transition_unit_state(unit, UnitState.PARKED, author=author, store=store)

    return RedirectResponse(url="/board", status_code=303)


async def board_skip_view(request: Request) -> Response:
    """Handle skip action for a unit, unblocking downstream dependents."""
    store: StoreProtocol = request.app.state.store
    form_data = await request.form()
    unit_id = str(form_data.get("unit_id", "")).strip().upper()

    unit = store.get_unit(unit_id)
    if unit and unit.state in (UnitState.BLOCKED, UnitState.READY, UnitState.RETURNED):
        author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
        transition_unit_state(unit, UnitState.SKIPPED, author=author, store=store)

    return RedirectResponse(url="/board", status_code=303)


async def board_reset_view(request: Request) -> Response:
    """Handle reset/rework action for a dispatched, returned, or parked unit."""
    store: StoreProtocol = request.app.state.store
    form_data = await request.form()
    unit_id = str(form_data.get("unit_id", "")).strip().upper()

    unit = store.get_unit(unit_id)
    if unit and unit.state in (UnitState.DISPATCHED, UnitState.RETURNED, UnitState.PARKED):
        author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
        transition_unit_state(unit, UnitState.READY, author=author, store=store)

    return RedirectResponse(url="/board", status_code=303)


async def board_refresh_view(request: Request) -> Response:
    """Explicitly trigger sync refresh and re-evaluate ready states on demand (BOARD-06)."""
    store: StoreProtocol = request.app.state.store
    store.sync_refresh()

    vault_dir = getattr(store, "vault_dir", None)
    if vault_dir:
        runtime = WorkflowRuntime(store=store, vault_dir=vault_dir)
        author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
        for wfl in runtime.list_workflows():
            runtime.refresh_workflow_states(wfl.id, author=author)

    return RedirectResponse(url="/board", status_code=303)
