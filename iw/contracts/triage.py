"""Triage protocol definition."""

from typing import Protocol, runtime_checkable
from iw.contracts.models import Author, InboxItem, Node


@runtime_checkable
class TriageProtocol(Protocol):
    """Layer 2 triage service contract for converting raw inbox items to nodes."""

    def list_inbox_items(self) -> list[InboxItem]:
        """Fetch pending raw items from the inbox."""
        ...

    def triage_item(self, item_id: str, node: Node, author: Author) -> Node:
        """Convert an inbox item into a typed, saved node and clear from inbox."""
        ...

    def defer_item(self, item_id: str) -> None:
        """Keep an inbox item for later review without converting."""
        ...

    def discard_item(self, item_id: str) -> bool:
        """Delete an inbox item without converting."""
        ...

    def return_to_inbox(self, node_id: str, author: Author) -> InboxItem | None:
        """Undo triage: push node body/text back to inbox and delete the node."""
        ...

