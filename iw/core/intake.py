"""Intake and drop folder ingestion service.

Layer 1 Core component for scanning dropped media/documents and creating stub notes.
"""

from pathlib import Path
from typing import Any

from iw.contracts.models import Author, Node

IMAGE_EXTENSIONS = {".png", ".svg", ".jpg", ".jpeg", ".gif", ".webp"}
TEXT_EXTENSIONS = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".py", ".log"}
TYPE_PREFIXES: dict[str, str] = {
    "artifact": "ART",
    "source": "SRC",
    "observation": "OBS",
    "idea": "IDEA",
    "friction": "FRI",
    "question": "QUE",
    "experiment": "EXP",
    "asset": "AST",
}


class IntakeManager:
    """Manages dropped reference files, diagrams, and sketches in iw-vault/drop/."""

    def __init__(self, drop_dir: Path, store: Any) -> None:
        self.drop_dir = drop_dir
        self.store = store

    def _cleanup_legacy_inbox_drop(self) -> None:
        """Migrate any files in legacy inbox/drop into drop/ and remove the folder."""
        inbox_drop = self.drop_dir.parent / "inbox" / "drop"
        if inbox_drop.exists() and inbox_drop.is_dir() and inbox_drop != self.drop_dir:
            self.drop_dir.mkdir(parents=True, exist_ok=True)
            for p in sorted(inbox_drop.iterdir()):
                if p.is_file() and not p.name.startswith("."):
                    target = self.drop_dir / p.name
                    if not target.exists():
                        p.rename(target)
            try:
                if not any(inbox_drop.iterdir()):
                    inbox_drop.rmdir()
            except OSError:
                pass

    def list_dropped_files(self) -> list[Path]:
        """Scan and return all media or document files in the drop directory."""
        self._cleanup_legacy_inbox_drop()
        self.drop_dir.mkdir(parents=True, exist_ok=True)
        return [
            p for p in sorted(self.drop_dir.iterdir())
            if p.is_file() and not p.name.startswith(".")
        ]

    def intake_file(self, file_name: str, node: Node, author: Author) -> Node:
        """Convert a dropped file into a stub node with attached media/document."""
        node_type = node.type.lower()
        prefix = TYPE_PREFIXES.get(node_type, "ART")
        node_id = node.id.strip().upper() if node.id and node.id.strip() else self.store.allocate_id(prefix)

        rel_drop = f"drop/{file_name}"
        attrs = dict(node.attrs)
        attrs["rendered_file"] = rel_drop

        body = node.body.strip() if node.body else self._default_embed(file_name, node.title, rel_drop)

        node_to_save = Node(
            id=node_id,
            type=node_type,
            title=node.title.strip(),
            created=node.created,
            domain=node.domain.strip() if node.domain else "general",
            tags=[t.strip() for t in node.tags if t.strip()],
            state=node.state if node.state else "active",
            edges=node.edges,
            body=body,
            attrs=attrs,
        )

        return self.store.write_node(node_to_save, author)

    def attach_file_to_node(self, file_name: str, target_node_id: str, author: Author) -> Node | None:
        """Attach a dropped file to an existing mature node."""
        target = self.store.get_node(target_node_id)
        if target is None:
            return None

        rel_drop = f"drop/{file_name}"
        embed = self._default_embed(file_name, file_name, rel_drop)
        updated_body = f"{target.body}\n\n{embed}".strip() if target.body else embed

        updated = Node(
            id=target.id,
            type=target.type,
            title=target.title,
            created=target.created,
            domain=target.domain,
            tags=target.tags,
            state=target.state,
            edges=target.edges,
            body=updated_body,
            attrs=target.attrs,
        )
        return self.store.write_node(updated, author)

    def _default_embed(self, file_name: str, title: str, rel_path: str) -> str:
        """Generate markdown embed, imported text, or link for the dropped file."""
        ext = Path(file_name).suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            return f"![{title}]({rel_path})\n\nExported sketch / visual capture."
        if ext in TEXT_EXTENSIONS:
            drop_path = self.drop_dir / file_name
            if drop_path.exists() and drop_path.is_file():
                try:
                    content = drop_path.read_text(encoding="utf-8", errors="replace").strip()
                    if content:
                        return f"{content}\n\n---\n*Reference file: [{file_name}]({rel_path})*"
                except Exception:
                    pass
        return f"[{file_name}]({rel_path})\n\nAttached reference document / datasheet."
