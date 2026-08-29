"""YAML Frontmatter parsing and serialization utilities for all node types and edges.

Layer 1 Core module. Depends only on iw.contracts, stdlib, and yaml.
"""

from datetime import datetime, timezone
import re
from typing import Any
import yaml

from iw.contracts.models import AttentionItem, Author, AuthorKind, Edge, Node

RESERVED_KEYS = {
    "id", "type", "title", "created", "domain", "tags",
    "state", "last_touched", "author", "attrs", "edges",
}


def parse_author(raw: Any) -> Author | None:
    """Extract Author dataclass from raw frontmatter dict."""
    if not isinstance(raw, dict) or "kind" not in raw:
        return None
    return Author(
        kind=AuthorKind(raw["kind"]),
        courier=raw.get("courier", "web-ui"),
        requested_model=raw.get("requested_model"),
        declared_model=raw.get("declared_model"),
    )


def serialize_author(author: Author) -> dict[str, Any]:
    """Serialize Author dataclass into frontmatter dictionary."""
    return {
        "kind": author.kind.value,
        "courier": author.courier,
        "requested_model": author.requested_model,
        "declared_model": author.declared_model,
    }


def parse_datetime(val: Any) -> datetime:
    """Parse ISO datetime string or return datetime object."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def parse_edge(data: Any, default_from_id: str) -> Edge | None:
    """Parse single edge dictionary into Edge object."""
    if not isinstance(data, dict):
        return None
    from_id = str(data.get("from", default_from_id)).upper()
    to_id = str(data.get("to", "")).upper()
    relation = str(data.get("relation", ""))
    if not to_id or not relation:
        return None
    created_dt = parse_datetime(data.get("created"))
    author = parse_author(data.get("author")) or Author(kind=AuthorKind.HUMAN, courier="web-ui")
    return Edge(
        from_id=from_id,
        to_id=to_id,
        relation=relation,
        created=created_dt,
        author=author,
        confidence=float(data.get("confidence", 1.0)),
        note=str(data.get("note", "")),
    )


def serialize_edge(edge: Edge) -> dict[str, Any]:
    """Serialize Edge dataclass into dictionary."""
    return {
        "from": edge.from_id,
        "to": edge.to_id,
        "relation": edge.relation,
        "created": edge.created.isoformat() if edge.created else datetime.now(timezone.utc).isoformat(),
        "author": serialize_author(edge.author) if edge.author else serialize_author(Author(kind=AuthorKind.HUMAN, courier="web-ui")),
        "confidence": edge.confidence,
        "note": edge.note,
    }


def build_node_from_frontmatter(data: dict[str, Any], body: str) -> Node:
    """Construct Node object from parsed frontmatter dictionary and body."""
    node_id = str(data["id"]).upper()
    created_dt = parse_datetime(data.get("created"))
    touched_val = data.get("last_touched")
    touched_dt = parse_datetime(touched_val) if touched_val else None

    # Collect custom and type-specific attributes
    attrs: dict[str, Any] = dict(data.get("attrs", {}))
    for k, v in data.items():
        if k not in RESERVED_KEYS and k not in attrs:
            attrs[k] = v

    raw_edges = data.get("edges", [])
    edges: list[Edge] = []
    if isinstance(raw_edges, list):
        for item in raw_edges:
            edge = parse_edge(item, node_id)
            if edge is not None:
                edges.append(edge)

    return Node(
        id=node_id,
        type=str(data.get("type", "friction")),
        title=str(data.get("title", "")),
        created=created_dt,
        domain=str(data.get("domain", "")),
        tags=list(data.get("tags", [])),
        state=str(data.get("state", "active")),
        author=parse_author(data.get("author")),
        last_touched=touched_dt,
        body=body,
        attrs=attrs,
        edges=edges,
    )


def parse_node_from_text(
    text: str, filepath: str
) -> tuple[Node | None, AttentionItem | None]:
    """Parse markdown text with YAML frontmatter into Node or AttentionItem."""
    now = datetime.now(timezone.utc)
    if not text.startswith("---"):
        return None, AttentionItem(filepath, "Missing YAML frontmatter", now)

    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, AttentionItem(filepath, "Malformed fence delimiters", now)

    try:
        data = yaml.safe_load(parts[1])
    except Exception as err:
        return None, AttentionItem(filepath, f"YAML parse error: {err}", now)

    if not isinstance(data, dict):
        return None, AttentionItem(filepath, "Frontmatter is not a mapping", now)

    node_id = data.get("id")
    if not node_id or not isinstance(node_id, str) or not node_id.strip():
        return None, AttentionItem(filepath, "Missing or invalid id", now)

    body = parts[2].lstrip("\r\n")
    return build_node_from_frontmatter(data, body), None


def merge_frontmatter(
    existing: dict[str, Any],
    node: Node,
    clean_id: str,
    author: Author,
    now: datetime,
) -> dict[str, Any]:
    """Merge updated node fields and attributes while preserving untouched keys."""
    out = dict(existing)
    out["id"] = clean_id
    out["type"] = node.type
    out["title"] = node.title
    created_str = node.created.isoformat() if node.created else str(existing.get("created") or now.isoformat())
    out["created"] = created_str
    out["domain"] = node.domain
    out["tags"] = node.tags
    out["state"] = node.state
    out["last_touched"] = now.isoformat()
    out["author"] = serialize_author(author)

    if node.attrs:
        for k, v in node.attrs.items():
            out[k] = v

    # Derive CML for ideas if scores are present (DA-03 §03)
    if node.type == "idea" and "scores" in out and isinstance(out["scores"], dict):
        score_vals = [v for v in out["scores"].values() if isinstance(v, (int, float))]
        if score_vals:
            out["cml"] = int(min(score_vals))

    if node.edges:
        out["edges"] = [serialize_edge(e) for e in node.edges]

    return out


def slugify_title(title: str, fallback_id: str) -> str:
    """Convert node title into filesystem-friendly slug."""
    slug = re.sub(r"[^\w\-]+", "-", title.lower()).strip("-")[:40]
    return slug if slug else fallback_id.lower()
