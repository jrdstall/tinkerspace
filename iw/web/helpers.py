"""Web helper utilities for facet extraction and graph edge resolution.

Layer 4 Web surface helper.
"""

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
