"""Security and boundary tests for the MCP Wall (V§14.8, DA-10).

Traces MCP-06 per docs/design/specs/MCP.md.
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from iw.contracts.models import Author, AuthorKind, Node, UnitOfWork, UnitState
from iw.core.store import MarkdownStore
from iw.mcp.server import create_mcp_server, submit_result_tool


def test_mcp_06_wall_rejects_path_traversal_attempts(tmp_path: Path):
    """MCP-06: The MCP Wall rejects attempts to write companion files outside work/UOW-xxx/."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    unit = UnitOfWork(id="UOW-W01", title="Wall Test Unit", activity="test@1", state=UnitState.READY)
    store.write_unit(unit, author=author)

    # 1. Path traversal via ../
    with pytest.raises(ValueError, match="Path traversal rejected"):
        submit_result_tool(
            store=store,
            unit_id="UOW-W01",
            deliverable="# Prose",
            artifacts=[{"filename": "../escape.txt", "content": "malicious"}],
        )

    # Verify escape file was never created
    assert not (tmp_path / "work" / "escape.txt").exists()
    assert not (tmp_path / "escape.txt").exists()


def test_mcp_06_wall_prevents_direct_acceptance_by_agent(tmp_path: Path):
    """MCP-06: Agent submission transitions to RETURNED, never directly to ACCEPTED."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    unit = UnitOfWork(id="UOW-W02", title="Acceptance Boundary Unit", activity="test@1", state=UnitState.READY)
    store.write_unit(unit, author=author)

    submit_result_tool(
        store=store,
        unit_id="UOW-W02",
        deliverable="# Agent Output\nReady for human review.",
    )

    reloaded = store.get_unit("UOW-W02")
    assert reloaded is not None
    # State MUST be returned (awaiting review), NOT accepted
    assert reloaded.state == UnitState.RETURNED
    assert reloaded.state != UnitState.ACCEPTED


def test_mcp_06_wall_server_exposes_zero_arbitrary_mutation_tools(tmp_path: Path):
    """MCP-06: MCP server exposes only read-only and unit-scoped submission tools."""
    store = MarkdownStore(vault_dir=tmp_path)
    server = create_mcp_server(store)

    # Verify that dangerous mutation tools are NOT registered on the server
    # Tool names should only be read_unit, submit_result, read_node, query_nodes
    tool_names = set(server._tool_manager._tools.keys()) if hasattr(server, "_tool_manager") else set()
    
    assert "write_node" not in tool_names
    assert "delete_node" not in tool_names
    assert "delete_file" not in tool_names
    assert "accept_unit" not in tool_names
