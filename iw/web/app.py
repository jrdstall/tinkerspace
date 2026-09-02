"""Tinkerspace ASGI Web Application."""

import os
from pathlib import Path
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route
from starlette.templating import Jinja2Templates

from iw.adapters.git import GitCommitter
from iw.contracts.models import QueryFilters
from iw.contracts.store import StoreProtocol
from iw.core.events import FileEventLog
from iw.core.index import InMemoryIndex
from iw.core.store import MarkdownStore
from iw.domain.scout.service import ScoutService
from iw.web.helpers import extract_facets, resolve_inbound_edges
from iw.web import (
    association_views, board_views, intake_views, maturity_views,
    node_views, planner_views, question_views, scout_views, triage_views, workflow_views,
)

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_default_store() -> StoreProtocol:
    vault_str = os.environ.get("IW_VAULT_DIR")
    v_path = Path(vault_str).resolve() if vault_str else Path(__file__).resolve().parent.parent.parent / "iw-vault"
    v_path.mkdir(parents=True, exist_ok=True)
    return MarkdownStore(v_path, event_log=FileEventLog(v_path / "events.jsonl"), git_committer=GitCommitter(v_path))


async def index_view(request: Request) -> Response:
    store: StoreProtocol = request.app.state.store
    store.sync_refresh()
    all_nodes = store.list_nodes()
    corpus_nodes = [n for n in all_nodes if not (n.attrs.get("is_subquestion") is True or (n.type == "question" and bool(n.attrs.get("subject_id"))))]
    q, n_type = request.query_params.get("q", "").strip(), request.query_params.get("type", "").strip()
    domain, tag = request.query_params.get("domain", "").strip(), request.query_params.get("tag", "").strip()
    state, sort_by = request.query_params.get("state", "").strip(), request.query_params.get("sort", "touched").strip()
    filters = QueryFilters(type=n_type or None, domain=domain or None, tag=tag or None, state=state or None)
    filtered = InMemoryIndex(corpus_nodes).filter_and_search(filters, query_text=q or None, sort_by=sort_by)

    scout = ScoutService(store.vault_dir / "meta" / "scout_interests.json")
    offers = scout.get_stale_offers()

    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "request": request, "nodes": filtered, "total_nodes": len(corpus_nodes),
            "attention_items": store.list_needs_attention(), "inbox_count": len(store.list_inbox()),
            "drop_count": len(store.list_dropped_files()), "facets": extract_facets(corpus_nodes),
            "offers": offers, "q": q, "current_type": n_type, "current_domain": domain,
            "current_tag": tag, "current_state": state, "current_sort": sort_by,
        },
    )


async def capture_view(request: Request) -> Response:
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


async def vault_file_view(request: Request) -> Response:
    store: StoreProtocol = request.app.state.store
    rel = request.path_params.get("filepath", "")
    if ".." in rel or rel.startswith("/") or rel.startswith("\\"):
        return Response("Forbidden", status_code=403)
    target = (store.vault_dir / rel).resolve()
    if not str(target).startswith(str(store.vault_dir.resolve())) or not target.is_file():
        return Response("Not Found", status_code=404)
    return FileResponse(target)


async def _view_node(r: Request) -> Response: return await node_views.node_detail_view(r, templates)
async def _view_maturity(r: Request) -> Response: return await maturity_views.maturity_view(r, templates)
async def _view_assoc(r: Request) -> Response: return await association_views.association_deck_view(r, templates)
async def _view_board(r: Request) -> Response: return await board_views.board_view(r, templates)
async def _view_workflow(r: Request) -> Response: return await workflow_views.workflow_view(r, templates)
async def _view_planner(r: Request) -> Response: return await planner_views.planner_view(r, templates)
async def _view_scout(r: Request) -> Response: return await scout_views.scout_view(r, templates)
async def _view_qgraph(r: Request) -> Response: return await question_views.question_graph_view(r, templates)
async def _view_triage(r: Request) -> Response: return await triage_views.triage_view(r, templates)
async def _view_intake(r: Request) -> Response: return await intake_views.intake_view(r, templates)


def _get_core_routes() -> list[Route]:
    return [
        Route("/", endpoint=index_view, methods=["GET"]),
        Route("/node/{node_id}", endpoint=_view_node, methods=["GET"]),
        Route("/node/{node_id}/link", endpoint=node_views.node_link_action, methods=["POST"]),
        Route("/node/{node_id}/unlink", endpoint=node_views.node_unlink_action, methods=["POST"]),
        Route("/vault-file/{filepath:path}", endpoint=vault_file_view, methods=["GET"]),
        Route("/capture", endpoint=capture_view, methods=["POST"]),
        Route("/maturity", endpoint=_view_maturity, methods=["GET"]),
        Route("/associations", endpoint=_view_assoc, methods=["GET"]),
        Route("/associations/keep", endpoint=association_views.association_keep_action, methods=["POST"]),
        Route("/associations/discard", endpoint=association_views.association_discard_action, methods=["POST"]),
        Route("/associations/generate", endpoint=association_views.association_generate_action, methods=["POST"]),
        Route("/board", endpoint=_view_board, methods=["GET"]),
        Route("/workboard", endpoint=_view_board, methods=["GET"]),
        Route("/workflow/{workflow_id}", endpoint=_view_workflow, methods=["GET"]),
    ]


def _get_feature_routes() -> list[Route]:
    return [
        Route("/ideas/{idea_id}/plan", endpoint=_view_planner, methods=["GET"]),
        Route("/ideas/{idea_id}/plan/instantiate", endpoint=planner_views.planner_instantiate_action, methods=["POST"]),
        Route("/ideas/{idea_id}/plan/custom_instantiate", endpoint=planner_views.planner_custom_instantiate_action, methods=["POST"]),
        Route("/scout", endpoint=_view_scout, methods=["GET"]),
        Route("/scout/new", endpoint=scout_views.scout_create_action, methods=["POST"]),
        Route("/scout/{interest_id}/dismiss", endpoint=scout_views.scout_dismiss_action, methods=["POST"]),
        Route("/scout/{interest_id}/sweep", endpoint=scout_views.scout_sweep_action, methods=["POST"]),
        Route("/question-graph/{subject_id}", endpoint=_view_qgraph, methods=["GET"]),
        Route("/question-graph/create", endpoint=question_views.question_create_action, methods=["POST"]),
        Route("/question-graph/transform", endpoint=question_views.question_transform_action, methods=["POST"]),
        Route("/question-graph/link", endpoint=question_views.question_link_action, methods=["POST"]),
        Route("/board/dispatch", endpoint=board_views.board_dispatch_view, methods=["POST"]),
        Route("/board/collect", endpoint=board_views.board_collect_view, methods=["POST"]),
        Route("/board/park", endpoint=board_views.board_park_view, methods=["POST"]),
        Route("/board/skip", endpoint=board_views.board_skip_view, methods=["POST"]),
        Route("/board/reset", endpoint=board_views.board_reset_view, methods=["POST"]),
        Route("/board/refresh", endpoint=board_views.board_refresh_view, methods=["POST", "GET"]),
        Route("/board/action_guide", endpoint=board_views.board_edit_action_guide_view, methods=["POST"]),
        Route("/triage", endpoint=_view_triage, methods=["GET"]),
        Route("/triage/accept", endpoint=triage_views.triage_accept_view, methods=["POST"]),
        Route("/triage/discard", endpoint=triage_views.triage_discard_view, methods=["POST"]),
        Route("/triage/defer", endpoint=triage_views.triage_defer_view, methods=["POST"]),
        Route("/intake", endpoint=_view_intake, methods=["GET"]),
        Route("/intake/create", endpoint=intake_views.intake_create_view, methods=["POST"]),
        Route("/intake/attach", endpoint=intake_views.intake_attach_view, methods=["POST"]),
        Route("/intake/external", endpoint=intake_views.intake_external_view, methods=["POST"]),
        Route("/health", endpoint=lambda r: JSONResponse({"status": "ok", "app": "tinkerspace"}), methods=["GET"]),
    ]


def create_app(store: StoreProtocol | None = None) -> Starlette:
    routes = _get_core_routes() + _get_feature_routes()
    application = Starlette(debug=True, routes=routes)
    application.state.store = store if store is not None else get_default_store()
    return application


app = create_app()
