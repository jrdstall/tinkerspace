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

CANONICAL_DOMAINS: list[str] = [
    "Computing & Architecture",
    "Space Systems",
    "Defense & C2",
    "Mobility & Transportation",
    "Creativity & Expression",
    "Enterprise & Organization",
    "Health & Performance",
    "Living & Preparedness",
    "Learning & Education",
    "Tools & Prototyping",
]

DOMAIN_SUGGESTED_TAGS: dict[str, list[str]] = {
    "Computing & Architecture": ["ambient-computing", "contextual-profiles", "smart-data", "app-silos", "e-ink", "ai-agents"],
    "Space Systems": ["smallsat", "satellite-constellations", "mission-orchestration", "tactical-space", "real-time-c2"],
    "Defense & C2": ["tactical-c2", "isr", "sensor-networks", "cognitive-c2", "multi-int", "warfighter"],
    "Mobility & Transportation": ["cycling", "safety", "automotive", "lighting", "wearables", "camera-systems"],
    "Creativity & Expression": ["workspace-design", "craftsmanship", "apparel", "analog-art", "creative-exercises"],
    "Enterprise & Organization": ["rowe", "workplace-culture", "defense-contracting", "consulting", "team-dynamics"],
    "Health & Performance": ["nutrition", "calorie-tracking", "assistive-devices", "fitness-equipment", "wearables"],
    "Living & Preparedness": ["kitchen-tech", "hvac", "disaster-prep", "emergency-shelter", "retail", "personal-gear"],
    "Learning & Education": ["experiential-learning", "higher-ed", "assembly-line-learning", "pedagogy"],
    "Tools & Prototyping": ["3d-printing", "fdm", "electronics", "soldering", "fabrication"],
}


def sanitize_tags(raw_tags: list[str] | str, domain: str = "", node_type: str = "") -> list[str]:
    """Sanitize and normalize tags: strip hashes, split space-separated terms, drop type/domain echoes."""
    items: list[str] = []
    if isinstance(raw_tags, str):
        if "," in raw_tags:
            items = [t.strip() for t in raw_tags.split(",") if t.strip()]
        else:
            items = [t.strip() for t in raw_tags.split() if t.strip()]
    elif isinstance(raw_tags, list):
        for entry in raw_tags:
            entry_str = str(entry).strip()
            if "," in entry_str:
                items.extend([t.strip() for t in entry_str.split(",") if t.strip()])
            else:
                items.append(entry_str)

    drop_words = {node_type.strip().lower(), domain.strip().lower()}
    cleaned: list[str] = []
    for item in items:
        tok = item.lstrip("#").strip().lower().replace("_", "-")
        if tok and tok not in drop_words and tok not in cleaned:
            cleaned.append(tok)
    return cleaned



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
            tags=sanitize_tags(node.tags, domain=node.domain, node_type=node_type),
            state=node.state if node.state else "active",
            edges=edges,
            body=node.body,
            attrs=node.attrs,
        )

        saved = self.store.write_node(node_to_save, author)
        self.store.delete_inbox_item(item_id, author=author)
        return saved

    def defer_item(self, item_id: str) -> None:
        """Keep an inbox item for later review without converting."""
        # Defer keeps the item in the store inbox
        return None

    def discard_item(self, item_id: str) -> bool:
        """Delete an inbox item without converting."""
        return self.store.delete_inbox_item(item_id)

    def return_to_inbox(self, node_id: str, author: Author) -> InboxItem | None:
        """Undo triage: push node body/text back to inbox and delete the node."""
        node = self.store.get_node(node_id)
        if not node:
            return None
        raw_text = node.body.strip() if node.body and node.body.strip() else node.title
        item = self.store.append_inbox(raw_text=raw_text, inlet="triage-undo")
        self.store.delete_node(node_id, author=author)
        return item
