"""MCP Server surface and safe agent tool interface.

Implements MCP-01 through MCP-06 and enforces the MCP Wall (V§14.8) preventing unauthorized mutations.
"""

from pathlib import Path
from typing import Any
from mcp.server.mcpserver import MCPServer

from iw.contracts.store import StoreProtocol
from iw.mcp.tools import (
    list_units_tool,
    query_nodes_tool,
    read_node_tool,
    read_unit_tool,
    submit_result_tool,
    validate_safe_filename,
)

# Re-export tools for contract and behaviour test compatibility
_validate_safe_filename = validate_safe_filename


def _register_unit_tools(server: MCPServer, store: StoreProtocol) -> None:
    """Register unit of work lifecycle and submission tools."""

    @server.tool()
    def list_units(state: str | None = None) -> list[dict[str, Any]]:
        """List work units in the vault, optionally filtered by state (ready, blocked, dispatched, returned)."""
        return list_units_tool(store, state)

    @server.tool()
    def read_unit(unit_id: str) -> dict[str, Any]:
        """Fetch the Action Guide prompt, step objective, rubric, and idea context for a unit of work."""
        return read_unit_tool(store, unit_id)

    @server.tool()
    def submit_result(
        unit_id: str,
        deliverable: str,
        artifacts: list[dict[str, str]] | None = None,
        model_name: str | None = None,
    ) -> dict[str, Any]:
        """Submit completed deliverable markdown (with summary, verdict, scores header) and optional companion files."""
        return submit_result_tool(store, unit_id, deliverable, artifacts, model_name)


def _register_node_tools(server: MCPServer, store: StoreProtocol) -> None:
    """Register read-only node inspection and query tools."""

    @server.tool()
    def read_node(node_id: str) -> dict[str, Any] | None:
        """Fetch a specific node (idea, friction, question, observation, asset) from the vault by ID (read-only)."""
        return read_node_tool(store, node_id)

    @server.tool()
    def query_nodes(
        type_filter: str | None = None,
        domain_filter: str | None = None,
        tag_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search and filter permanent vault nodes by type, domain, or tag (read-only)."""
        return query_nodes_tool(store, type_filter, domain_filter, tag_filter)


def create_mcp_server(store: StoreProtocol) -> MCPServer:
    """Instantiate and configure the MCP server with unit-scoped safe tools."""
    server = MCPServer("tinkerspace")
    _register_unit_tools(server, store)
    _register_node_tools(server, store)
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
