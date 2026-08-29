"""Layer 1/2 Triage service implementation.

Converts raw inbox items into typed nodes with deterministic IDs,
stamped human author attribution, and edge link relationships.
"""

from iw.contracts.models import Author, Edge, InboxItem, Node
from iw.contracts.store import StoreProtocol
from iw.contracts.triage import TriageProtocol

TYPE_PREFIXES: dict[str, str] = {
    "friction": "FRI",
    "observation": "OBS",
    "idea": "IDEA",
    "question": "QUE",
    "experiment": "EXP",
    "asset": "AST",
    "artifact": "ART",
    "source": "SRC",
}


class TriageService(TriageProtocol):
    """Service orchestrating rapid keyboard triage passes over inbox items."""

    def __init__(self, store: StoreProtocol) -> None:
        self.store = store

    def list_inbox_items(self) -> list[InboxItem]:
        """Fetch pending raw items from the store inbox."""
        return self.store.list_inbox()

    def triage_item(self, item_id: str, node: Node, author: Author) -> Node:
        """Convert an inbox item into a typed, saved node and clear from inbox."""
        node_type = node.type.lower()
        prefix = TYPE_PREFIXES.get(node_type, node_type[:3].upper())
        node_id = node.id.strip().upper() if node.id and node.id.strip() else self.store.allocate_id(prefix)

        edges = [
            Edge(
                from_id=e.from_id if e.from_id else node_id,
                to_id=e.to_id,
                relation=e.relation,
                created=e.created,
                author=e.author,
                confidence=e.confidence,
                note=e.note,
            )
            for e in node.edges
        ]

        node_to_save = Node(
            id=node_id,
            type=node_type,
            title=node.title.strip(),
            created=node.created,
            domain=node.domain.strip() if node.domain else "general",
            tags=[t.strip() for t in node.tags if t.strip()],
            state=node.state if node.state else "active",
            edges=edges,
            body=node.body,
            attrs=node.attrs,
        )

        saved = self.store.write_node(node_to_save, author)
        self.store.delete_inbox_item(item_id)
        return saved

    def defer_item(self, item_id: str) -> None:
        """Keep an inbox item for later review without converting."""
        # Defer keeps the item in the store inbox
        return None

    def discard_item(self, item_id: str) -> bool:
        """Delete an inbox item without converting."""
        return self.store.delete_inbox_item(item_id)
