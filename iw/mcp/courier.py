"""MCP Courier implementation.

Manages agent work order delivery, result payload retrieval, and attribution stamping for MCP interactions.
"""

from pathlib import Path
from typing import Any

from iw.contracts.courier import CourierProtocol
from iw.contracts.models import Author, AuthorKind
from iw.contracts.store import StoreProtocol


class MCPCourier:
    """Layer 3 courier connecting AI agents to unit folders via MCP."""

    def __init__(self, store: StoreProtocol, vault_dir: Path | None = None) -> None:
        self._store = store
        self._vault_dir = vault_dir if vault_dir is not None else getattr(store, "vault_dir", Path("."))

    @property
    def name(self) -> str:
        """Courier identifier."""
        return "mcp"

    def deliver_order(self, unit_id: str, payload: dict[str, Any]) -> bool:
        """Deliver work order prompt and instructions into the unit directory."""
        clean_id = unit_id.strip().upper()
        folder = self._vault_dir / "work" / clean_id
        folder.mkdir(parents=True, exist_ok=True)

        prompt_text = payload.get("prompt", "")
        if prompt_text:
            (folder / "prompt.md").write_text(prompt_text, encoding="utf-8")
        return True

    def retrieve_result(self, unit_id: str) -> dict[str, Any] | None:
        """Retrieve output result files for an order."""
        clean_id = unit_id.strip().upper()
        folder = self._vault_dir / "work" / clean_id
        deliv_file = folder / "deliverable.md"
        if not deliv_file.exists():
            return None
        return {
            "deliverable": deliv_file.read_text(encoding="utf-8"),
            "files": [p.name for p in folder.iterdir() if p.is_file()],
        }

    def build_mcp_author(self, declared_model: str | None = None) -> Author:
        """Build agent Author record stamped with MCP courier and declared model (MCP-04)."""
        return Author(
            kind=AuthorKind.AGENT,
            courier="mcp",
            declared_model=declared_model,
        )
