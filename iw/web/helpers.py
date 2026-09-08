"""Web helper utilities for facet extraction and graph edge resolution.

Layer 4 Web surface helper.
"""

from typing import Any
from urllib.parse import urlparse
from starlette.requests import Request
from iw.contracts.models import Node
from iw.contracts.store import StoreProtocol


def extract_facets(nodes: list[Node]) -> dict[str, list[str]]:
    """Extract unique filter facet options from a node collection."""
    return {
        "domains": sorted(list(set(n.domain for n in nodes if n.domain))),
        "tags": sorted(list(set(t for n in nodes for t in n.tags if t))),
        "types": sorted(list(set(n.type for n in nodes if n.type))),
        "states": sorted(list(set(n.state for n in nodes if n.state))),
    }


def resolve_inbound_edges(nodes: list[Node], target_id: str) -> list[dict[str, str]]:
    """Find all edges in the node list pointing to the target node ID."""
    clean_target = target_id.upper()
    inbound: list[dict[str, str]] = []
    for other in nodes:
        for e in other.edges:
            if e.to_id.upper() == clean_target:
                inbound.append({
                    "from_id": other.id,
                    "relation": e.relation,
                    "from_title": other.title,
                })
    return inbound


def _resolve_artifact_meta(target: Node | None, note: str, store: StoreProtocol | None) -> dict[str, str]:
    """Resolve unit and deliverable metadata for an artifact node."""
    attrs = target.attrs if target else {}
    u_id = str(attrs.get("unit", "")).strip().upper()
    if not u_id and "UOW-" in note.upper():
        cleaned = note.replace(":", " ").replace("(", " ").replace(")", " ")
        for w in cleaned.split():
            if w.upper().startswith("UOW-"):
                u_id = w.upper()
                break
    u_title = str(attrs.get("unit_title", "")).strip()
    if not u_title and u_id and store:
        unit = store.get_unit(u_id)
        if unit and unit.title:
            u_title = unit.title
    fname = str(attrs.get("file_name", "")).strip() or note
    fpath = str(attrs.get("path", "")).strip()
    is_gen = target.title.startswith("deliverable.md for ") if (target and target.title) else False
    title = (u_title or target.title) if is_gen else ((target.title if target else "") or u_title)
    ctx = f"{u_id}: {u_title}" if (u_id and u_title) else (u_id or u_title or note)
    return {"display_title": title, "unit_id": u_id, "unit_title": u_title, "file_name": fname, "file_path": fpath, "context_note": ctx}


def _build_edge_dict(edge: Any, target: Node | None, art_info: dict[str, str], is_art: bool, ttype: str) -> dict[str, Any]:
    return {
        "to_id": edge.to_id, "relation": edge.relation, "note": edge.note,
        "to_title": target.title if target else "", "to_type": ttype, "is_artifact": is_art,
        "display_title": art_info.get("display_title", target.title if target else ""),
        "context_note": art_info.get("context_note", edge.note),
        "file_path": art_info.get("file_path", ""), "file_name": art_info.get("file_name", ""),
        "unit_id": art_info.get("unit_id", ""),
    }


def resolve_outbound_edges(
    node: Node, all_nodes: list[Node], store: StoreProtocol | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Resolve outbound links with titles, types, and rich artifact deliverable metadata."""
    nodes_by_id = {n.id.upper(): n for n in all_nodes}
    outbound: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    for edge in node.edges:
        tid = edge.to_id.upper()
        target = nodes_by_id.get(tid)
        ttype = target.type if target else ("artifact" if tid.startswith("ART-") else "")
        is_art = (ttype == "artifact") or tid.startswith("ART-")
        art_info = _resolve_artifact_meta(target, edge.note, store) if is_art else {}
        ed = _build_edge_dict(edge, target, art_info, is_art, ttype)
        outbound.append(ed)
        if is_art:
            artifacts.append({
                "id": edge.to_id, "title": ed["display_title"] or edge.to_id, "relation": edge.relation,
                "unit_id": art_info.get("unit_id", ""), "unit_title": art_info.get("unit_title", ""),
                "file_name": art_info.get("file_name", ""), "file_path": art_info.get("file_path", ""),
                "note": edge.note,
            })
    return outbound, artifacts


def format_node_back_label(target: Node) -> str:
    """Format human-friendly back button label for a node."""
    title_part = f": {target.title}" if target.title else ""
    if len(title_part) > 35:
        title_part = title_part[:32] + "..."
    return f"{target.type.capitalize()} ({target.id}{title_part})"


def resolve_from_param(from_param: str, current_node_id: str, store: StoreProtocol) -> tuple[str, str] | None:
    """Resolve back link from 'from' query parameter."""
    if not from_param:
        return None
    target = store.get_node(from_param.upper())
    if target is not None and target.id != current_node_id:
        return f"/node/{target.id}", format_node_back_label(target)
    known = {
        "board": ("/board", "Work Board"),
        "associations": ("/associations", "Association Deck"),
        "triage": ("/triage", "Triage Inbox"),
        "scout": ("/scout", "Technology Scout"),
        "explore": ("/", "Explore"),
    }
    return known.get(from_param.lower())


def resolve_referer_target(referer: str, current_node_id: str, store: StoreProtocol, netloc: str) -> tuple[str, str] | None:
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
                    return f"/node/{node.id}", format_node_back_label(node)
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


def resolve_back_target(request: Request, current_node_id: str, store: StoreProtocol) -> tuple[str, str]:
    """Resolve back navigation URL and label from query param or Referer header."""
    from_param = request.query_params.get("from", "").strip()
    result = resolve_from_param(from_param, current_node_id, store)
    if result is not None:
        return result
    referer = request.headers.get("referer", "").strip()
    ref_result = resolve_referer_target(referer, current_node_id, store, request.url.netloc)
    if ref_result is not None:
        return ref_result
    return "/", "Explore"


def resolve_adjacent_nodes(nodes: list[Node], current_node: Node) -> tuple[Node | None, Node | None]:
    """Find previous and next peer nodes of the same type ordered by recency."""
    peers = [n for n in nodes if n.type == current_node.type]
    sorted_peers = sorted(
        peers,
        key=lambda n: (n.last_touched or n.created or 0),
        reverse=True,
    )
    cur_id = current_node.id.upper()
    peer_ids = [n.id.upper() for n in sorted_peers]
    if cur_id not in peer_ids:
        return None, None
    idx = peer_ids.index(cur_id)
    prev_node = sorted_peers[idx - 1] if idx > 0 else None
    next_node = sorted_peers[idx + 1] if idx < len(sorted_peers) - 1 else None
    return prev_node, next_node
