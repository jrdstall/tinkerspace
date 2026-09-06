"""Node web views and relationship management routes.

Layer 4 Web surface module.
"""

from datetime import datetime, timezone
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.templating import Jinja2Templates

from iw.contracts.models import Author, AuthorKind, Edge, Node
from iw.contracts.store import StoreProtocol
from iw.web.helpers import resolve_adjacent_nodes, resolve_back_target, resolve_inbound_edges


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
    back_url, back_label = resolve_back_target(request, node_id, store)
    prev_node, next_node = resolve_adjacent_nodes(all_nodes, node)

    raw_keywords = node.attrs.get("keywords", [])
    keywords_list = raw_keywords if isinstance(raw_keywords, list) else [raw_keywords] if raw_keywords else []
    keywords_display = ", ".join(str(k) for k in keywords_list)

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
            "prev_node": prev_node,
            "next_node": next_node,
            "keywords_list": keywords_list,
            "keywords_display": keywords_display,
            "tags_display": ", ".join(node.tags),
        },
    )


async def node_edit_action(request: Request) -> Response:
    """Update core note attributes and markdown prose atomically."""
    store: StoreProtocol = request.app.state.store
    node_id = request.path_params.get("node_id", "").strip().upper()
    node = store.get_node(node_id)
    if node is None:
        return HTMLResponse(f"<h1>404 Not Found</h1><p>Node '{node_id}' does not exist.</p>", status_code=404)

    form = await request.form()
    title = str(form.get("title", "")).strip() or node.title
    domain = str(form.get("domain", "")).strip() or node.domain
    state = str(form.get("state", "")).strip() or node.state
    tags = [t.strip().lstrip("#").strip() for t in str(form.get("tags", "")).split(",") if t.strip().lstrip("#").strip()]
    keywords = [k.strip().lstrip("#").strip() for k in str(form.get("keywords", "")).split(",") if k.strip().lstrip("#").strip()]
    body = str(form.get("body", "")).replace("\r\n", "\n").replace("\r", "\n")

    node.title, node.domain, node.state, node.tags, node.body = title, domain, state, tags, body
    if keywords:
        node.attrs["keywords"] = keywords
    elif "keywords" in node.attrs:
        del node.attrs["keywords"]

    if node.type == "idea":
        w_me = str(form.get("worth_to_me", "")).strip()
        w_others = str(form.get("worth_to_others", "")).strip()
        if w_me: node.attrs["worth_to_me"] = w_me
        if w_others: node.attrs["worth_to_others"] = w_others

    node.last_touched = datetime.now(timezone.utc)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    store.write_node(node, author=author)

    event_log = getattr(store, "event_log", None)
    if event_log is not None:
        event_log.append(kind="node_edited", subject_id=node.id, author=author, payload={"title": node.title})

    from_param = request.query_params.get("from", "").strip()
    redirect_url = f"/node/{node_id}?from={from_param}" if from_param else f"/node/{node_id}"
    return RedirectResponse(url=redirect_url, status_code=303)


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
