"""Node web views and relationship management routes.

Layer 4 Web surface module.
"""

from datetime import datetime, timezone
from urllib.parse import urlparse
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.templating import Jinja2Templates

from iw.contracts.models import Author, AuthorKind, Edge, Node
from iw.contracts.store import StoreProtocol
from iw.web.helpers import resolve_inbound_edges


def _count_questions(nodes: list[Node], subject_id: str) -> int:
    """Count question nodes attached to a subject node."""
    count = 0
    for n in nodes:
        if n.type == "question":
            for e in n.edges:
                if e.to_id == subject_id and e.relation == "questions":
                    count += 1
                    break
    return count


def _format_node_back_label(target: Node) -> str:
    """Format human-friendly back button label for a node."""
    title_part = f": {target.title}" if target.title else ""
    if len(title_part) > 35:
        title_part = title_part[:32] + "..."
    return f"{target.type.capitalize()} ({target.id}{title_part})"


def _resolve_from_param(from_param: str, current_node_id: str, store: StoreProtocol) -> tuple[str, str] | None:
    """Resolve back link from 'from' query parameter."""
    if not from_param:
        return None
    target = store.get_node(from_param.upper())
    if target is not None and target.id != current_node_id:
        return f"/node/{target.id}", _format_node_back_label(target)
    known = {
        "board": ("/board", "Work Board"),
        "associations": ("/associations", "Association Deck"),
        "triage": ("/triage", "Triage Inbox"),
        "scout": ("/scout", "Technology Scout"),
        "explore": ("/", "Explore"),
    }
    return known.get(from_param.lower())


def _resolve_referer_target(referer: str, current_node_id: str, store: StoreProtocol, netloc: str) -> tuple[str, str] | None:
    """Resolve back link from HTTP Referer header if on same origin."""
    if not referer:
        return None
    try:
        parsed = urlparse(referer)
        if parsed.netloc and parsed.netloc != netloc:
            return None
        path = parsed.path
        if path.startswith("/node/"):
            ref_id = path.split("/node/")[1].split("/")[0].upper()
            if ref_id and ref_id != current_node_id:
                node = store.get_node(ref_id)
                if node is not None:
                    return f"/node/{node.id}", _format_node_back_label(node)
        elif path.startswith("/question-graph/"):
            sub_id = path.split("/question-graph/")[1].split("/")[0].upper()
            return path, f"Question Graph ({sub_id})"
        elif path.startswith("/workflow/"):
            wfl_id = path.split("/workflow/")[1].split("/")[0].upper()
            return path, f"Workflow ({wfl_id})"
        routes = {"/board": "Work Board", "/associations": "Association Deck", "/triage": "Triage Inbox"}
        if path in routes:
            return path, routes[path]
    except Exception:
        pass
    return None


def _resolve_back_target(request: Request, current_node_id: str, store: StoreProtocol) -> tuple[str, str]:
    """Resolve back navigation URL and label from query param or Referer header."""
    from_param = request.query_params.get("from", "").strip()
    result = _resolve_from_param(from_param, current_node_id, store)
    if result is not None:
        return result
    referer = request.headers.get("referer", "").strip()
    ref_result = _resolve_referer_target(referer, current_node_id, store, request.url.netloc)
    if ref_result is not None:
        return ref_result
    return "/", "Explore"


async def node_detail_view(request: Request, templates: Jinja2Templates) -> Response:
    """Render the node detail view with frontmatter, edges, and relationship editor."""
    store: StoreProtocol = request.app.state.store
    node_id = request.path_params.get("node_id", "").strip().upper()
    node = store.get_node(node_id)
    if node is None:
        return HTMLResponse(f"<h1>404 Not Found</h1><p>Node '{node_id}' does not exist.</p>", status_code=404)

    all_nodes = store.list_nodes()
    available_targets = [n for n in all_nodes if n.id != node_id]
    inbound = resolve_inbound_edges(all_nodes, node_id)
    q_count = _count_questions(all_nodes, node_id)
    back_url, back_label = _resolve_back_target(request, node_id, store)

    return templates.TemplateResponse(
        request=request,
        name="node.html",
        context={
            "request": request,
            "node": node,
            "inbound_edges": inbound,
            "available_targets": available_targets,
            "question_count": q_count,
            "inbox_count": len(store.list_inbox()),
            "drop_count": len(store.list_dropped_files()),
            "back_url": back_url,
            "back_label": back_label,
        },
    )


async def node_link_action(request: Request) -> Response:
    """Add a typed directional relationship edge from this node to a target node."""
    store: StoreProtocol = request.app.state.store
    node_id = request.path_params.get("node_id", "").strip().upper()
    form = await request.form()
    raw_target = str(form.get("target_id", "")).strip()
    target_id = raw_target.split()[0].upper() if raw_target else ""
    relation = str(form.get("relation", "relates_to")).strip()
    note = str(form.get("note", "")).strip()

    if node_id and target_id and relation:
        node = store.get_node(node_id)
        target_node = store.get_node(target_id)
        if node is not None and target_node is not None:
            now = datetime.now(timezone.utc)
            author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
            already_linked = any(e.to_id == target_id and e.relation == relation for e in node.edges)
            if not already_linked:
                new_edge = Edge(
                    from_id=node.id,
                    to_id=target_node.id,
                    relation=relation,
                    created=now,
                    author=author,
                    note=note,
                )
                node.edges.append(new_edge)
                store.write_node(node, author=author)
                event_log = getattr(store, "event_log", None)
                if event_log is not None:
                    event_log.append(
                        kind="edge_created",
                        subject_id=node.id,
                        author=author,
                        payload={"from_id": node.id, "to_id": target_node.id, "relation": relation, "note": note},
                    )

    from_param = request.query_params.get("from", "").strip()
    redirect_url = f"/node/{node_id}?from={from_param}" if from_param else f"/node/{node_id}"
    return RedirectResponse(url=redirect_url, status_code=303)


async def node_unlink_action(request: Request) -> Response:
    """Remove a typed directional relationship edge from this node."""
    store: StoreProtocol = request.app.state.store
    node_id = request.path_params.get("node_id", "").strip().upper()
    form = await request.form()
    target_id = str(form.get("target_id", "")).strip().upper()
    relation = str(form.get("relation", "")).strip()

    if node_id and target_id:
        node = store.get_node(node_id)
        if node is not None:
            author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
            node.edges = [
                e for e in node.edges
                if not (e.to_id == target_id and (not relation or e.relation == relation))
            ]
            store.write_node(node, author=author)
            event_log = getattr(store, "event_log", None)
            if event_log is not None:
                event_log.append(
                    kind="edge_removed",
                    subject_id=node.id,
                    author=author,
                    payload={"from_id": node.id, "to_id": target_id, "relation": relation},
                )

    from_param = request.query_params.get("from", "").strip()
    redirect_url = f"/node/{node_id}?from={from_param}" if from_param else f"/node/{node_id}"
    return RedirectResponse(url=redirect_url, status_code=303)
