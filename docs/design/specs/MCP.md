# MCP — Subsystem Behaviour Specifications

MCP-01  An AI agent connecting over MCP can call `read_unit(unit_id)` and receive the unit metadata, Action Guide, subject nodes, and input files.
MCP-02  An AI agent can call `submit_result(unit_id, deliverable_text, artifacts, model_name)` over MCP, writing `deliverable.md` and companion files into `work/<UOW-id>/`.
MCP-03  Submitting a result over MCP transitions the unit of work state to `returned` (Awaiting Review).
MCP-04  Results submitted via MCP stamp author attribution with `courier: "mcp"` and the declared model name.
MCP-05  An AI agent can call read-only query and exploration tools (`read_node(node_id)`, `query_nodes(...)`) without modifying store state.
MCP-06  The MCP Wall strictly prevents agents from writing directly to nodes outside `work/<UOW-id>/`, deleting files, or accepting units directly.
MCP-07  All MCP tools expose descriptive documentation (docstrings) for schema discovery and agent prompt orientation.

