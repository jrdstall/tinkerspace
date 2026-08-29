"""Web helper utilities for facet extraction and graph edge resolution.

Layer 4 Web surface helper.
"""

from iw.contracts.models import Node


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
