"""Behaviour tests for MCP Courier and Agent tools.

Traces MCP-01 through MCP-05 per docs/design/specs/MCP.md.
"""

from datetime import datetime, timezone
from pathlib import Path

from iw.contracts.models import Author, AuthorKind, Node, UnitOfWork, UnitState
from iw.core.store import MarkdownStore
from iw.mcp.server import (
    query_nodes_tool,
    read_node_tool,
    read_unit_tool,
    submit_result_tool,
)


from iw.core.events import FileEventLog


def _setup_store_with_context(tmp_path: Path) -> MarkdownStore:
    event_log = FileEventLog(log_path=tmp_path / "system" / "events.jsonl")
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    idea = Node(
        id="IDEA-A01",
        type="idea",
        title="Sunlight Display",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["display"],
        body="Low-power sunlight readable display for bikes.",
    )
    store.write_node(idea, author=author)

    unit = UnitOfWork(
        id="UOW-A01",
        title="Prior Art Survey",
        activity="prior-art-survey@1",
        state=UnitState.READY,
        subject_ids=["IDEA-A01"],
        action_guide="Search USPTO for low power transflective LCD patents.",
    )
    store.write_unit(unit, author=author)

    work_folder = tmp_path / "work" / "UOW-A01"
    work_folder.mkdir(parents=True, exist_ok=True)
    (work_folder / "baseline-specs.txt").write_text("500 nits minimum", encoding="utf-8")

    return store


def test_mcp_01_read_unit_provides_action_guide_and_subject_context(tmp_path: Path):
    """MCP-01: Agent can read unit of work, Action Guide, subject nodes, and input files."""
    store = _setup_store_with_context(tmp_path)

    res = read_unit_tool(store, "UOW-A01")

    assert res["id"] == "UOW-A01"
    assert "Search USPTO" in res["action_guide"]
    assert len(res["subject_nodes"]) == 1
    assert res["subject_nodes"][0]["id"] == "IDEA-A01"
    assert "Sunlight Display" in res["subject_nodes"][0]["title"]
    assert "baseline-specs.txt" in res["input_files"]


def test_mcp_02_submit_result_writes_deliverable_and_companion_files(tmp_path: Path):
    """MCP-02: Agent can submit deliverable markdown and companion artifact files."""
    store = _setup_store_with_context(tmp_path)

    deliv_text = "---\nunit: UOW-A01\nsummary: Patent search complete\n---\n# Results\nFound 3 patents."
    artifacts = [{"filename": "patents.csv", "content": "id,title\n1,transflective"}]

    res = submit_result_tool(
        store=store,
        unit_id="UOW-A01",
        deliverable=deliv_text,
        artifacts=artifacts,
        model_name="claude-3-7-sonnet-20250219",
    )

    assert res["status"] == "submitted"
    work_folder = tmp_path / "work" / "UOW-A01"
    assert (work_folder / "deliverable.md").exists()
    assert (work_folder / "patents.csv").exists()
    assert "Found 3 patents." in (work_folder / "deliverable.md").read_text(encoding="utf-8")


def test_mcp_03_submit_result_transitions_unit_to_returned(tmp_path: Path):
    """MCP-03: Submitting result over MCP transitions unit state to returned."""
    store = _setup_store_with_context(tmp_path)

    submit_result_tool(
        store=store,
        unit_id="UOW-A01",
        deliverable="# Done\nAll items resolved.",
        model_name="claude-3-7-sonnet-20250219",
    )

    reloaded = store.get_unit("UOW-A01")
    assert reloaded is not None
    assert reloaded.state == UnitState.RETURNED


def test_mcp_04_mcp_attribution_stamps_courier_and_declared_model(tmp_path: Path):
    """MCP-04: Submissions stamp author attribution with courier: 'mcp' and declared model."""
    store = _setup_store_with_context(tmp_path)

    submit_result_tool(
        store=store,
        unit_id="UOW-A01",
        deliverable="# Done\nResults.",
        model_name="claude-3-7-sonnet-20250219",
    )

    # Unit write events should reflect MCP courier
    events = store.event_log.read_events()
    mcp_events = [e for e in events if e.author and e.author.courier == "mcp"]
    assert len(mcp_events) > 0
    assert mcp_events[-1].author.declared_model == "claude-3-7-sonnet-20250219"
    assert mcp_events[-1].author.kind == AuthorKind.AGENT


def test_mcp_05_read_only_query_tools_do_not_modify_state(tmp_path: Path):
    """MCP-05: Read-only query tools return results without modifying store state."""
    store = _setup_store_with_context(tmp_path)
    initial_events_count = len(store.event_log.read_events())

    node_data = read_node_tool(store, "IDEA-A01")
    assert node_data is not None
    assert node_data["id"] == "IDEA-A01"

    results = query_nodes_tool(store, type_filter="idea", domain_filter="hardware")
    assert len(results) == 1
    assert results[0]["id"] == "IDEA-A01"

    # Verify zero event log entries added
    assert len(store.event_log.read_events()) == initial_events_count


async def test_mcp_07_all_tools_have_non_empty_descriptions(tmp_path: Path):
    """MCP-07: All tools exposed by create_mcp_server provide descriptive documentation."""
    from iw.mcp.server import create_mcp_server

    store = _setup_store_with_context(tmp_path)
    server = create_mcp_server(store)
    tools = await server.list_tools()

    assert len(tools) >= 5
    for t in tools:
        assert t.description is not None
        assert len(t.description.strip()) > 10, f"Tool '{t.name}' has empty or too short description"

