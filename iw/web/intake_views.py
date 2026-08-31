"""Intake web view routes and dropped media / external note ingestion handlers.

Layer 4 Web surface component.
"""

from datetime import datetime, timezone
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.templating import Jinja2Templates

from iw.contracts.models import Author, AuthorKind, Node
from iw.contracts.store import StoreProtocol
from iw.domain.intake.external import ingest_external_node


async def intake_view(request: Request, templates: Jinja2Templates) -> Response:
    """Render intake surface with pending dropped sketches, documents, and backlog items."""
    store: StoreProtocol = request.app.state.store
    store.sync_refresh()
    dropped = store.list_dropped_files()
    nodes = store.list_nodes()
    return templates.TemplateResponse(
        request=request,
        name="intake.html",
        context={
            "request": request,
            "dropped_files": dropped,
            "all_nodes": nodes,
            "drop_count": len(dropped),
            "inbox_count": len(store.list_inbox()),
        },
    )


async def intake_create_view(request: Request) -> Response:
    """Convert a dropped file into a new stub node."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    file_name = str(form.get("file_name", "")).strip()
    node_type = str(form.get("node_type", "artifact")).strip()
    title = str(form.get("title", file_name)).strip()
    domain = str(form.get("domain", "general")).strip()
    tags = [t.strip() for t in str(form.get("tags", "")).split(",") if t.strip()]
    body = str(form.get("body", "")).strip()
    now = datetime.now(timezone.utc)
    author = Author(kind=AuthorKind.HUMAN, courier="intake-surface")

    node = Node(id="", type=node_type, title=title, created=now, domain=domain, tags=tags, state="active", body=body)
    saved = store.intake_file(file_name=file_name, node=node, author=author)
    return RedirectResponse(url=f"/node/{saved.id}", status_code=303)


async def intake_attach_view(request: Request) -> Response:
    """Attach a dropped file to an existing mature node."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    file_name = str(form.get("file_name", "")).strip()
    target_id = str(form.get("target_id", "")).strip().upper()
    author = Author(kind=AuthorKind.HUMAN, courier="intake-surface")

    if hasattr(store, "intake_manager"):
        store.intake_manager.attach_file_to_node(file_name=file_name, target_node_id=target_id, author=author)
    return RedirectResponse(url=f"/node/{target_id}", status_code=303)


async def intake_external_view(request: Request) -> Response:
    """Ingest an external markdown note from another vault (EXTINT-01..04)."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    raw_text = str(form.get("content", "")).strip()
    source_vault = str(form.get("source_vault", "external")).strip()
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    if raw_text:
        saved = ingest_external_node(store, raw_text, source_vault, author)
        return RedirectResponse(url=f"/node/{saved.id}", status_code=303)
    return RedirectResponse(url="/intake", status_code=303)
