"""MCP Server surface and safe agent tool interface.

Implements MCP-01 through MCP-06 and enforces the MCP Wall (V§14.8) preventing unauthorized mutations.
"""

from pathlib import Path
import re
from typing import Any
from mcp.server.mcpserver import MCPServer

from iw.contracts.models import Author, AuthorKind, Node, QueryFilters, UnitOfWork, UnitState
from iw.contracts.store import StoreProtocol
from iw.domain.workflow.state import transition_unit_state
from iw.mcp.courier import MCPCourier


def _validate_safe_filename(filename: str) -> str:
    """Ensure artifact filenames do not contain path traversal characters (MCP-06)."""
    clean = Path(filename).name
    if ".." in filename or "/" in filename or "\\" in filename or not clean:
        raise ValueError(f"Path traversal rejected: '{filename}' (MCP-06)")
    return clean


def read_unit_tool(store: StoreProtocol, unit_id: str) -> dict[str, Any]:
    """Fetch unit of work record, Action Guide, and subject node context for an agent (MCP-01)."""
    clean_id = unit_id.strip().upper()
    unit = store.get_unit(clean_id)
    if not unit:
        raise ValueError(f"Unit of work '{clean_id}' not found")

    vault_dir = getattr(store, "vault_dir", Path("."))
    folder = vault_dir / "work" / clean_id
    input_files = [p.name for p in folder.iterdir() if p.is_file() and p.name not in ("unit.yaml", "deliverable.md")] if folder.exists() else []

    subject_data: list[dict[str, Any]] = []
    for sub_id in unit.subject_ids:
        node = store.get_node(sub_id)
        if node:
            subject_data.append({"id": node.id, "type": node.type, "title": node.title, "body": node.body, "attrs": node.attrs})

    return {
        "id": unit.id,
        "title": unit.title,
        "activity": unit.activity,
        "state": unit.state.value,
        "action_guide": unit.action_guide,
        "subject_nodes": subject_data,
        "input_files": input_files,
    }


def submit_result_tool(
    store: StoreProtocol,
    unit_id: str,
    deliverable: str,
    artifacts: list[dict[str, str]] | None = None,
    model_name: str | None = None,
) -> dict[str, Any]:
    """Write deliverable and companion files to work folder and transition unit to RETURNED (MCP-02..04, 06)."""
    clean_id = unit_id.strip().upper()
    unit = store.get_unit(clean_id)
    if not unit:
        raise ValueError(f"Unit '{clean_id}' not found")

    vault_dir = getattr(store, "vault_dir", Path("."))
    folder = vault_dir / "work" / clean_id
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "deliverable.md").write_text(deliverable, encoding="utf-8")

    saved_files: list[str] = ["deliverable.md"]
    if artifacts:
        for art in artifacts:
            safe_name = _validate_safe_filename(art.get("filename", "output.txt"))
            content = art.get("content", "")
            (folder / safe_name).write_text(content, encoding="utf-8")
            saved_files.append(safe_name)

    courier = MCPCourier(store=store, vault_dir=vault_dir)
    author = courier.build_mcp_author(declared_model=model_name)

    if unit.state != UnitState.RETURNED:
        if unit.state == UnitState.READY:
            transition_unit_state(unit, UnitState.DISPATCHED, author=author, store=store)
        transition_unit_state(unit, UnitState.RETURNED, author=author, store=store)

    return {"status": "submitted", "unit_id": clean_id, "state": "returned", "files_saved": saved_files}


def read_node_tool(store: StoreProtocol, node_id: str) -> dict[str, Any] | None:
    """Read-only node retrieval tool for exploration (MCP-05)."""
    node = store.get_node(node_id.strip().upper())
    if not node:
        return None
    return {
        "id": node.id,
        "type": node.type,
        "title": node.title,
        "domain": node.domain,
        "tags": node.tags,
        "body": node.body,
        "attrs": node.attrs,
    }


def query_nodes_tool(
    store: StoreProtocol,
    type_filter: str | None = None,
    domain_filter: str | None = None,
    tag_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Read-only multi-facet search across the vault (MCP-05)."""
    nodes = store.list_nodes(type_filter=type_filter)
    results: list[dict[str, Any]] = []
    for n in nodes:
        if domain_filter and n.domain.lower() != domain_filter.lower():
            continue
        if tag_filter and tag_filter.lower() not in [t.lower() for t in n.tags]:
            continue
        results.append({"id": n.id, "type": n.type, "title": n.title, "domain": n.domain, "tags": n.tags})
    return results


def create_mcp_server(store: StoreProtocol) -> MCPServer:
    """Instantiate and configure the MCP server with unit-scoped safe tools."""
    server = MCPServer("tinkerspace")

    @server.tool()
    def read_unit(unit_id: str) -> dict[str, Any]:
        return read_unit_tool(store, unit_id)

    @server.tool()
    def submit_result(
        unit_id: str,
        deliverable: str,
        artifacts: list[dict[str, str]] | None = None,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        return submit_result_tool(store, unit_id, deliverable, artifacts, model_name)

    @server.tool()
    def read_node(node_id: str) -> dict[str, Any] | None:
        return read_node_tool(store, node_id)

    @server.tool()
    def query_nodes(
        type_filter: str | None = None,
        domain_filter: str | None = None,
        tag_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        return query_nodes_tool(store, type_filter, domain_filter, tag_filter)

    return server


def main() -> None:
    """Run the Tinkerspace MCP server over stdio transport (MCP-01..06)."""
    import argparse
    import os
    from iw.core.store import MarkdownStore

    parser = argparse.ArgumentParser(description="Tinkerspace MCP Server")
    parser.add_argument(
        "--vault",
        type=str,
        default=os.environ.get("IW_VAULT_DIR", r"C:\Users\jrdst\software\IW\vault"),
        help="Path to Tinkerspace vault directory",
    )
    args = parser.parse_args()
    vault_path = Path(args.vault).resolve()
    store = MarkdownStore(vault_path)
    server = create_mcp_server(store)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

