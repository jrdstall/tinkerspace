"""Document helpers for reading and previewing attached files in the web UI.

Layer 4 Web surface helper module.
"""

from pathlib import Path
import re
from typing import Any

from iw.contracts.models import Node

TEXT_EXTENSIONS: set[str] = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".py", ".log"}
IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}
PDF_EXTENSIONS: set[str] = {".pdf"}
LINK_PATTERN: re.Pattern[str] = re.compile(r"\]\(((?:drop|attachments)/[^)]+)\)")


def _format_size(size_bytes: int) -> str:
    """Format file size in bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _extract_candidate_paths(node: Node, artifacts: list[dict[str, Any]]) -> list[str]:
    """Collect unique candidate file paths from node attributes, artifacts, and body links."""
    candidates: list[str] = []
    rf = str(node.attrs.get("rendered_file", "")).strip()
    if rf:
        candidates.append(rf)
    for art in artifacts:
        fp = str(art.get("file_path", "")).strip()
        if fp:
            candidates.append(fp)
    if node.body:
        for match in LINK_PATTERN.finditer(node.body):
            candidates.append(match.group(1).strip())
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for c in candidates:
        if c and c not in seen and ".." not in c:
            seen.add(c)
            unique.append(c)
    return unique


def _build_doc_item(vault_dir: Path, rel_path: str) -> dict[str, Any] | None:
    """Build a document item dictionary for an existing readable or media file."""
    target = (vault_dir / rel_path).resolve()
    try:
        target.relative_to(vault_dir.resolve())
    except ValueError:
        return None
    if not target.is_file():
        return None

    ext = target.suffix.lower()
    size = target.stat().st_size
    is_text = ext in TEXT_EXTENSIONS
    content: str = ""
    line_count: int = 0
    if is_text and size <= 100_000:
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            line_count = len(content.splitlines())
        except Exception:
            content = ""

    return {
        "name": target.name,
        "path": rel_path.replace("\\", "/"),
        "ext": ext,
        "size_bytes": size,
        "size_display": _format_size(size),
        "is_text": is_text,
        "is_markdown": ext == ".md",
        "is_image": ext in IMAGE_EXTENSIONS,
        "is_pdf": ext in PDF_EXTENSIONS,
        "content": content,
        "line_count": line_count,
    }


def resolve_attached_documents(
    node: Node, store: Any, artifacts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Discover, inspect, and read attached and linked files for a node."""
    vault_dir = getattr(store, "vault_dir", None)
    if not vault_dir or not isinstance(vault_dir, Path):
        return []

    docs: list[dict[str, Any]] = []
    for rel_path in _extract_candidate_paths(node, artifacts):
        item = _build_doc_item(vault_dir, rel_path)
        if item is not None:
            docs.append(item)
    return docs
