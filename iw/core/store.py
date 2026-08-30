"""Layer 1 Markdown Store implementation.

Reads and writes markdown files with YAML frontmatter and unit.yaml atomically from disk.
Enforces zero-caching, atomic rename, author attribution, ID allocation, inbox, and intake drop.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iw.contracts.event_log import EventLogProtocol
from iw.contracts.models import (
    AttentionItem,
    Author,
    AuthorKind,
    InboxItem,
    Node,
    UnitOfWork,
)
from iw.contracts.store import StoreProtocol
from iw.core.frontmatter import merge_frontmatter
from iw.core.ids import allocate_next_id
from iw.core.inbox import InboxManager
from iw.core.intake import IntakeManager
from iw.core.io import (
    atomic_write_markdown,
    build_node_path,
    find_file_by_id,
    parse_vault_file,
    read_raw_frontmatter_and_body,
    scan_vault_markdown_files,
)
from iw.core.units import atomic_write_unit_yaml, read_unit_yaml, scan_vault_units


class MarkdownStore(StoreProtocol):
    """Atomic filesystem store for markdown nodes and machine state."""

    def __init__(
        self,
        vault_dir: Path,
        event_log: EventLogProtocol | None = None,
        git_committer: Any | None = None,
    ) -> None:
        self.vault_dir = vault_dir
        self.event_log = event_log
        self.git_committer = git_committer
        self.inbox_manager = InboxManager(vault_dir / "inbox")
        self.intake_manager = IntakeManager(vault_dir / "drop", store=self)

    def get_node(self, node_id: str) -> Node | None:
        """Fetch a node by ID from disk. Never cached."""
        target_id = node_id.strip().upper()
        for path in scan_vault_markdown_files(self.vault_dir):
            node, _ = parse_vault_file(path)
            if node is not None and node.id.upper() == target_id:
                return node
        return None

    def list_nodes(self, type_filter: str | None = None) -> list[Node]:
        """Scan and return all valid nodes from the vault."""
        nodes: list[Node] = []
        for path in scan_vault_markdown_files(self.vault_dir):
            node, _ = parse_vault_file(path)
            if node is not None and (type_filter is None or node.type.lower() == type_filter.lower()):
                nodes.append(node)
        return nodes

    def list_needs_attention(self) -> list[AttentionItem]:
        """Return all quarantined unparseable, missing-id, or conflict files."""
        items: list[AttentionItem] = []
        for path in scan_vault_markdown_files(self.vault_dir):
            _, attention = parse_vault_file(path)
            if attention is not None:
                items.append(attention)
        return items

    def allocate_id(self, prefix: str) -> str:
        """Deterministically allocate the next sequence ID for an entity prefix."""
        known_ids = [node.id for node in self.list_nodes()]
        if self.event_log:
            for event in self.event_log.read_events():
                if event.subject_id:
                    known_ids.append(event.subject_id)
        return allocate_next_id(prefix, known_ids)

    def write_node(self, node: Node, author: Author) -> Node:
        """Write node frontmatter and body atomically to disk."""
        if not author or not author.kind:
            raise ValueError("Author with kind is required on write (STORE-11)")

        clean_id = node.id.strip().upper()
        now = datetime.now(timezone.utc)
        target_file = find_file_by_id(self.vault_dir, clean_id)

        existing_fm, existing_body = ({}, "")
        if target_file and target_file.exists():
            existing_fm, existing_body = read_raw_frontmatter_and_body(target_file)

        merged_fm = merge_frontmatter(existing_fm, node, clean_id, author, now)
        final_body = node.body if node.body else existing_body
        final_path = target_file or build_node_path(self.vault_dir, node.type, node.title, clean_id, now)

        atomic_write_markdown(final_path, merged_fm, final_body)
        self._record_node_mutation(clean_id, node, author, final_path)

        updated = self.get_node(clean_id)
        if updated is None:
            raise RuntimeError(f"Failed to read back written node {clean_id}")
        return updated

    def sync_refresh(self) -> list[str]:
        """Discover and commit external notes arriving via sync without background watchers."""
        synced_ids: list[str] = []
        if self.git_committer and hasattr(self.git_committer, "commit_all_uncommitted"):
            sync_author = Author(kind=AuthorKind.EXTERNAL, courier="sync")
            for path in self.git_committer.commit_all_uncommitted(sync_author, "sync: ingest notes"):
                if path.suffix == ".md" and path.exists():
                    node, _ = parse_vault_file(path)
                    node_id = node.id if node else path.stem
                    synced_ids.append(node_id)
                    if self.event_log:
                        self.event_log.append("node_synced", node_id, sync_author, {"path": str(path)})
        return synced_ids

    def list_inbox(self) -> list[InboxItem]:
        """Scan and return all raw captured items in the inbox."""
        return self.inbox_manager.list_items()

    def append_inbox(self, raw_text: str, inlet: str = "quick-capture", source_filename: str | None = None) -> InboxItem:
        """Append a raw captured thought to the store inbox."""
        item = self.inbox_manager.append_item(raw_text, inlet, source_filename)
        if self.event_log:
            self.event_log.append("inbox_captured", item.id, Author(AuthorKind.HUMAN, inlet), {"text": item.raw_text})
        return item

    def delete_inbox_item(self, item_id: str) -> bool:
        """Remove a processed or discarded inbox item from disk."""
        return self.inbox_manager.delete_item(item_id)

    def list_dropped_files(self) -> list[Path]:
        """Scan and return all media or document files in the drop directory."""
        return self.intake_manager.list_dropped_files()

    def intake_file(self, file_name: str, node: Node, author: Author) -> Node:
        """Convert a dropped file into a stub node with attached media."""
        return self.intake_manager.intake_file(file_name, node, author)

    def get_unit(self, unit_id: str) -> UnitOfWork | None:
        """Read a work unit and its unit.yaml state without caching."""
        target_id = unit_id.strip().upper()
        unit_file = self.vault_dir / "work" / target_id / "unit.yaml"
        if unit_file.exists():
            return read_unit_yaml(unit_file)
        for unit in scan_vault_units(self.vault_dir):
            if unit.id.upper() == target_id:
                return unit
        return None

    def write_unit(self, unit: UnitOfWork, author: Author) -> UnitOfWork:
        """Write unit.yaml state atomically into work/UOW-xxx/."""
        if not author or not author.kind:
            raise ValueError("Author with kind is required on unit write (UOW-08)")
        clean_id = unit.id.strip().upper()
        target_file = atomic_write_unit_yaml(self.vault_dir / "work" / clean_id, unit)
        if self.event_log:
            self.event_log.append("unit_written", clean_id, author, {"state": str(unit.state.value)})
        if self.git_committer:
            self.git_committer.commit_file(target_file, f"update {clean_id}: {unit.title}", author)
        updated = self.get_unit(clean_id)
        if updated is None:
            raise RuntimeError(f"Failed to read back written unit {clean_id}")
        return updated

    def list_units(self) -> list[UnitOfWork]:
        """Scan and return all work units from the vault."""
        return scan_vault_units(self.vault_dir)

    def _record_node_mutation(self, clean_id: str, node: Node, author: Author, path: Path) -> None:
        """Record write event to event log and trigger local git commit."""
        if self.event_log:
            self.event_log.append("node_written", clean_id, author, {"type": node.type, "title": node.title})
        if self.git_committer:
            self.git_committer.commit_file(path, f"update {clean_id}: {node.title}", author)
