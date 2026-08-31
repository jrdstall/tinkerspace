"""External Node Intake and Foreign ID Routing.

Implements EXTINT-01 through EXTINT-05 for ingesting foreign vault notes with collision handling.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml

from iw.contracts.models import Author, Edge, Node
from iw.contracts.store import StoreProtocol
from iw.core.frontmatter import parse_node_from_text


def _resolve_node_id(
    store: StoreProtocol,
    node: Node,
    id_map: dict[str, str],
    source_vault: str,
) -> tuple[str, bool]:
    """Resolve node ID, preserving non-colliding IDs and re-allocating on collision (EXTINT-02, 03)."""
    raw_id = (node.id or "").strip().upper()
    existing = store.get_node(raw_id) if raw_id else None

    if raw_id and not existing:
        id_map[raw_id] = raw_id
        return raw_id, False

    # Collision or missing ID: allocate next local ID
    prefix = raw_id.split("-")[0] if "-" in raw_id else node.type[:3].upper()
    if not prefix or len(prefix) < 3:
        prefix = "IDE"
    new_id = store.allocate_id(prefix)
    if raw_id:
        id_map[raw_id] = new_id
        node.attrs["foreign_id"] = raw_id
    return new_id, True


def _prepare_external_node(
    raw_text: str,
    source_vault: str,
    source_filename: str = "",
) -> Node:
    """Parse raw text into Node structure with fallback for zero-frontmatter files (EXTINT-01)."""
    parsed_node, _ = parse_node_from_text(raw_text, source_filename)
    if parsed_node:
        return parsed_node

    # Fallback for plain markdown files without full frontmatter
    fm: dict[str, Any] = {}
    body = raw_text
    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            try:
                loaded = yaml.safe_load(parts[1])
                if isinstance(loaded, dict):
                    fm = loaded
                body = parts[2].lstrip("\r\n")
            except Exception:
                pass

    title = Path(source_filename).stem if source_filename else "Imported Note"
    return Node(
        id="",
        type=str(fm.get("type", "idea")),
        title=str(fm.get("title", title)),
        created=datetime.now(timezone.utc),
        domain=str(fm.get("domain", "general")),
        tags=[str(t) for t in fm.get("tags", []) if isinstance(t, str)],
        body=body,
        attrs={k: v for k, v in fm.items() if k not in ("id", "type", "title", "created", "domain", "tags")},
    )


def ingest_external_node(
    store: StoreProtocol,
    raw_text: str,
    source_vault: str,
    author: Author,
    source_filename: str = "",
) -> Node:
    """Ingest a single external markdown note into the local vault (EXTINT-01..04)."""
    node = _prepare_external_node(raw_text, source_vault, source_filename)
    id_map: dict[str, str] = {}
    target_id, _ = _resolve_node_id(store, node, id_map, source_vault)
    node.id = target_id

    # Append source vault tag (EXTINT-04)
    vault_tag = f"vault:{source_vault.strip().lower()}"
    if vault_tag not in [t.lower() for t in node.tags]:
        node.tags.append(vault_tag)

    return store.write_node(node, author=author)


def ingest_external_bundle(
    store: StoreProtocol,
    files: list[tuple[str, str]],
    source_vault: str,
    author: Author,
) -> list[Node]:
    """Ingest multiple external notes, resolving ID collisions and remapping edges (EXTINT-05)."""
    parsed_nodes: list[Node] = []
    id_map: dict[str, str] = {}

    for fname, text in files:
        n = _prepare_external_node(text, source_vault, fname)
        target_id, _ = _resolve_node_id(store, n, id_map, source_vault)
        n.id = target_id
        vault_tag = f"vault:{source_vault.strip().lower()}"
        if vault_tag not in [t.lower() for t in n.tags]:
            n.tags.append(vault_tag)
        parsed_nodes.append(n)

    # Remap inter-node edges using id_map (EXTINT-05)
    now = datetime.now(timezone.utc)
    for n in parsed_nodes:
        remapped_edges: list[Edge] = []
        for e in n.edges:
            new_from = id_map.get(e.from_id.upper(), e.from_id.upper())
            new_to = id_map.get(e.to_id.upper(), e.to_id.upper())
            remapped_edges.append(
                Edge(from_id=new_from, to_id=new_to, relation=e.relation, created=e.created or now, author=author, note=e.note)
            )
        n.edges = remapped_edges

    return [store.write_node(n, author=author) for n in parsed_nodes]
