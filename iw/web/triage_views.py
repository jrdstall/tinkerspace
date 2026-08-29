"""Triage web view routes and action handlers.

Layer 4 Web surface component.
"""

from datetime import datetime, timezone
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.templating import Jinja2Templates

from iw.contracts.models import Author, AuthorKind, Edge, Node
from iw.contracts.store import StoreProtocol
from iw.core.triage import TriageService


async def triage_view(request: Request, templates: Jinja2Templates) -> Response:
    """Render rapid keyboard triage view."""
    store: StoreProtocol = request.app.state.store
    inbox_items = store.list_inbox()
    skip = int(request.query_params.get("skip", 0))
    current_index = min(skip, max(0, len(inbox_items) - 1)) if inbox_items else 0
    active_item = inbox_items[current_index] if inbox_items else None
    return templates.TemplateResponse(
        request=request,
        name="triage.html",
        context={
            "request": request,
            "item": active_item,
            "current_index": current_index,
            "total_items": len(inbox_items),
            "inbox_count": len(inbox_items),
            "drop_count": len(store.list_dropped_files()),
        },
    )


async def triage_accept_view(request: Request) -> Response:
    """Accept and convert raw inbox item to typed node."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    item_id = str(form.get("item_id", "")).strip()
    node_type = str(form.get("node_type", "friction")).strip()
    title = str(form.get("title", "")).strip()
    domain = str(form.get("domain", "general")).strip()
    tags = [t.strip() for t in str(form.get("tags", "")).split(",") if t.strip()]
    body = str(form.get("body", "")).strip()
    edge_target = str(form.get("edge_target", "")).strip().upper()
    edge_rel = str(form.get("edge_rel", "")).strip()
    now = datetime.now(timezone.utc)
    author = Author(kind=AuthorKind.HUMAN, courier="triage-surface")

    edges = [Edge(from_id="", to_id=edge_target, relation=edge_rel, created=now, author=author)] if edge_target and edge_rel else []
    node = Node(id="", type=node_type, title=title, created=now, domain=domain, tags=tags, state="active", edges=edges, body=body)
    TriageService(store).triage_item(item_id=item_id, node=node, author=author)
    return RedirectResponse(url="/triage", status_code=303)


async def triage_discard_view(request: Request) -> Response:
    """Discard raw inbox item."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    item_id = str(form.get("item_id", "")).strip()
    if item_id:
        store.delete_inbox_item(item_id)
    return RedirectResponse(url="/triage", status_code=303)


async def triage_defer_view(request: Request) -> Response:
    """Defer raw inbox item to next pass."""
    skip = int(request.query_params.get("skip", 0)) + 1
    return RedirectResponse(url=f"/triage?skip={skip}", status_code=303)
