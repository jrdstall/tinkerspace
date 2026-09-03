"""Safe agent tool implementations behind the MCP Wall.

Governed by MCP-01 through MCP-06 and Vision §14.8.
"""

from pathlib import Path
from typing import Any

from iw.contracts.models import Node, UnitOfWork, UnitState
from iw.contracts.store import StoreProtocol
from iw.domain.workflow.state import transition_unit_state
from iw.mcp.courier import MCPCourier


def validate_safe_filename(filename: str) -> str:
    """Ensure artifact filenames do not contain path traversal characters (MCP-06)."""
    clean = Path(filename).name
    if ".." in filename or "/" in filename or "\\" in filename or not clean:
        raise ValueError(f"Path traversal rejected: '{filename}' (MCP-06)")
    return clean


from iw.domain.workflow.prompt import compose_full_prompt


def _get_subject_context(store: StoreProtocol, subject_ids: list[str]) -> tuple[list[dict[str, Any]], Node | None]:
    """Retrieve structured dictionary and primary node for subject IDs."""
    data: list[dict[str, Any]] = []
    primary: Node | None = None
    for sub_id in subject_ids:
        node = store.get_node(sub_id)
        if node:
            if primary is None:
                primary = node
            data.append({"id": node.id, "type": node.type, "title": node.title, "body": node.body, "attrs": node.attrs})
    return data, primary


def read_unit_tool(store: StoreProtocol, unit_id: str) -> dict[str, Any]:
    """Fetch unit of work record, Action Guide, and subject node context for an agent (MCP-01)."""
    clean_id = unit_id.strip().upper()
    unit = store.get_unit(clean_id)
    if not unit:
        raise ValueError(f"Unit of work '{clean_id}' not found")

    vault_dir = getattr(store, "vault_dir", Path("."))
    folder = vault_dir / "work" / clean_id
    input_files = (
        [p.name for p in folder.iterdir() if p.is_file() and p.name not in ("unit.yaml", "deliverable.md")]
        if folder.exists()
        else []
    )

    subject_data, primary_subject = _get_subject_context(store, unit.subject_ids)
    full_prompt = compose_full_prompt(
        unit_id=unit.id,
        unit_title=unit.title,
        task_instructions=unit.action_guide,
        subject_node=primary_subject,
    )

    return {
        "id": unit.id,
        "title": unit.title,
        "activity": unit.activity,
        "state": unit.state.value,
        "action_guide": full_prompt,
        "prompt": full_prompt,
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
            safe_name = validate_safe_filename(art.get("filename", "output.txt"))
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


def list_units_tool(store: StoreProtocol, state_filter: str | None = None) -> list[dict[str, Any]]:
    """List work units in the vault, optionally filtered by state."""
    units = store.list_units()
    results: list[dict[str, Any]] = []
    for u in units:
        if state_filter and u.state.value.lower() != state_filter.lower():
            continue
        results.append({
            "id": u.id,
            "title": u.title,
            "activity": u.activity,
            "state": u.state.value,
            "subject_ids": u.subject_ids,
        })
    return results
