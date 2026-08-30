"""Tinkerspace ASGI Web Application.

Hosts the Starlette web UI and serves Explore, Node detail, Quick Capture, Triage, and Intake views.
"""

import os
from pathlib import Path
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
)
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from iw.adapters.git import GitCommitter
from iw.contracts.models import QueryFilters
from iw.contracts.store import StoreProtocol
from iw.core.events import FileEventLog
from iw.core.index import InMemoryIndex
from iw.core.store import MarkdownStore
from iw.web.helpers import extract_facets, resolve_inbound_edges
from iw.web import board_views, intake_views, triage_views

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_default_store() -> StoreProtocol:
    """Create default MarkdownStore from environment or default path."""
    vault_str = os.environ.get("IW_VAULT_DIR")
    vault_path = Path(vault_str).resolve() if vault_str else Path(__file__).resolve().parent.parent.parent / "iw-vault"
    vault_path.mkdir(parents=True, exist_ok=True)
    event_log = FileEventLog(vault_path / "events.jsonl")
    git_committer = GitCommitter(vault_dir=vault_path)
    return MarkdownStore(vault_dir=vault_path, event_log=event_log, git_committer=git_committer)


async def index_view(request: Request) -> Response:
    """Render the explore landing page with multi-facet filters and search."""
    store: StoreProtocol = request.app.state.store
    store.sync_refresh()
    all_nodes = store.list_nodes()
    q = request.query_params.get("q", "").strip()
    n_type = request.query_params.get("type", "").strip()
    domain = request.query_params.get("domain", "").strip()
    tag = request.query_params.get("tag", "").strip()
    state = request.query_params.get("state", "").strip()
    sort_by = request.query_params.get("sort", "touched").strip()

    filters = QueryFilters(type=n_type or None, domain=domain or None, tag=tag or None, state=state or None)
    filtered = InMemoryIndex(all_nodes).filter_and_search(filters, query_text=q or None, sort_by=sort_by)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "nodes": filtered,
            "total_nodes": len(all_nodes),
            "attention_items": store.list_needs_attention(),
            "inbox_count": len(store.list_inbox()),
            "drop_count": len(store.list_dropped_files()),
            "facets": extract_facets(all_nodes),
            "q": q,
            "current_type": n_type,
            "current_domain": domain,
            "current_tag": tag,
            "current_state": state,
            "current_sort": sort_by,
        },
    )


async def node_detail_view(request: Request) -> Response:
    """Render single node detail page with edge graphs and attributes."""
    store: StoreProtocol = request.app.state.store
    node_id = request.path_params.get("node_id", "").strip().upper()
    node = store.get_node(node_id)
    if node is None:
        return HTMLResponse(f"<h1>404 Not Found</h1><p>Node '{node_id}' does not exist.</p>", status_code=404)

    all_nodes = store.list_nodes()
    inbound_edges = resolve_inbound_edges(all_nodes, node_id)
    return templates.TemplateResponse(
        request=request,
        name="node.html",
        context={
            "request": request,
            "node": node,
            "inbound_edges": inbound_edges,
            "inbox_count": len(store.list_inbox()),
            "drop_count": len(store.list_dropped_files()),
        },
    )


async def capture_view(request: Request) -> Response:
    """Handle raw thought quick capture from web form or API."""
    store: StoreProtocol = request.app.state.store
    form_data = await request.form()
    raw_text = str(form_data.get("raw_text", "")).strip()
    stem = str(form_data.get("stem", "")).strip()

    full_text = f"{stem} {raw_text}".strip() if stem and not raw_text.startswith(stem) else raw_text
    if not full_text:
        return RedirectResponse(url="/", status_code=303)

    item = store.append_inbox(raw_text=full_text, inlet="quick-capture")
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"status": "ok", "id": item.id, "text": item.raw_text})

    return RedirectResponse(url="/", status_code=303)


async def board_entry_view(request: Request) -> Response:
    """Work Board entry delegating to board_views."""
    return await board_views.board_view(request, templates)


async def triage_entry_view(request: Request) -> Response:
    """Triage page entry delegating to triage_views."""
    return await triage_views.triage_view(request, templates)


async def intake_entry_view(request: Request) -> Response:
    """Intake page entry delegating to intake_views."""
    return await intake_views.intake_view(request, templates)


async def health_view(request: Request) -> JSONResponse:
    """Return service health status."""
    return JSONResponse({"status": "ok", "app": "tinkerspace"})


def create_app(store: StoreProtocol | None = None) -> Starlette:
    """Application factory configuring routes and store."""
    routes = [
        Route("/", endpoint=index_view, methods=["GET"]),
        Route("/node/{node_id}", endpoint=node_detail_view, methods=["GET"]),
        Route("/capture", endpoint=capture_view, methods=["POST"]),
        Route("/board", endpoint=board_entry_view, methods=["GET"]),
        Route("/workboard", endpoint=board_entry_view, methods=["GET"]),
        Route("/board/dispatch", endpoint=board_views.board_dispatch_view, methods=["POST"]),
        Route("/board/park", endpoint=board_views.board_park_view, methods=["POST"]),
        Route("/board/skip", endpoint=board_views.board_skip_view, methods=["POST"]),
        Route("/board/reset", endpoint=board_views.board_reset_view, methods=["POST"]),
        Route("/board/refresh", endpoint=board_views.board_refresh_view, methods=["POST", "GET"]),
        Route("/triage", endpoint=triage_entry_view, methods=["GET"]),
        Route("/triage/accept", endpoint=triage_views.triage_accept_view, methods=["POST"]),
        Route("/triage/discard", endpoint=triage_views.triage_discard_view, methods=["POST"]),
        Route("/triage/defer", endpoint=triage_views.triage_defer_view, methods=["POST"]),
        Route("/intake", endpoint=intake_entry_view, methods=["GET"]),
        Route("/intake/create", endpoint=intake_views.intake_create_view, methods=["POST"]),
        Route("/intake/attach", endpoint=intake_views.intake_attach_view, methods=["POST"]),
        Route("/health", endpoint=health_view, methods=["GET"]),
    ]
    application = Starlette(debug=True, routes=routes)
    application.state.store = store if store is not None else get_default_store()
    return application


app = create_app()

