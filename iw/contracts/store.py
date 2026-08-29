"""Store protocol definition."""

from pathlib import Path
from typing import Protocol, runtime_checkable
from iw.contracts.models import AttentionItem, Author, InboxItem, Node, UnitOfWork


@runtime_checkable
class StoreProtocol(Protocol):
    """Layer 1 storage contract for reading and writing nodes and work units."""

    def get_node(self, node_id: str) -> Node | None:
        """Fetch a node by ID from disk. Never cached."""
        ...

    def write_node(self, node: Node, author: Author) -> Node:
        """Write node frontmatter and body atomically to disk."""
        ...

    def list_nodes(self, type_filter: str | None = None) -> list[Node]:
        """Scan and return all nodes from the vault."""
        ...

    def get_unit(self, unit_id: str) -> UnitOfWork | None:
        """Read a work unit and its unit.yaml state."""
        ...

    def write_unit(self, unit: UnitOfWork, author: Author) -> UnitOfWork:
        """Write unit.yaml state atomically into work/UOW-xxx/."""
        ...

    def list_needs_attention(self) -> list[AttentionItem]:
        """Return all quarantined unparseable or sync-conflict files."""
        ...

    def allocate_id(self, prefix: str) -> str:
        """Deterministically allocate the next sequence ID for an entity prefix."""
        ...

    def sync_refresh(self) -> list[str]:
        """Discover and commit external notes arriving via sync."""
        ...

    def list_inbox(self) -> list[InboxItem]:
        """Scan and return all raw captured items in the inbox."""
        ...

    def append_inbox(
        self,
        raw_text: str,
        inlet: str = "quick-capture",
        source_filename: str | None = None,
    ) -> InboxItem:
        """Append a raw captured thought to the store inbox."""
        ...

    def delete_inbox_item(self, item_id: str) -> bool:
        """Remove a processed or discarded inbox item from disk."""
        ...

    def list_dropped_files(self) -> list[Path]:
        """Scan and return all media or document files in the drop directory."""
        ...

    def intake_file(self, file_name: str, node: Node, author: Author) -> Node:
        """Convert a dropped file into a stub node with attached media."""
        ...




