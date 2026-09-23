"""Context resolution and file staging service for Units of Work.

Governed by Vision §14.8, WORKFLOW-07, and MCP-01.
"""

from pathlib import Path
import shutil
from typing import Any

from iw.contracts.models import Node
from iw.contracts.store import StoreProtocol

TEXT_EXTENSIONS: set[str] = {
    ".md", ".txt", ".csv", ".json", ".yaml", ".yml",
    ".py", ".c", ".h", ".cpp", ".html", ".toml", ".sh",
}
MAX_EMBED_CHARS: int = 20_000


def _read_attachment_text(vault_dir: Path | None, fpath_rel: str, is_text: bool) -> str:
    """Read text content from vault file if existing and below truncation limit."""
    if not (is_text and vault_dir and fpath_rel):
        return ""
    full_path = vault_dir / fpath_rel
    if not (full_path.exists() and full_path.is_file()):
        return ""
    try:
        raw = full_path.read_text(encoding="utf-8")
        return raw[:MAX_EMBED_CHARS] + ("\n... [truncated]" if len(raw) > MAX_EMBED_CHARS else "")
    except Exception:
        return ""


def resolve_subject_attachments(
    subject_node: Node,
    store: StoreProtocol,
    vault_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Resolve attached artifact nodes and read file content for prompt injection (WORKFLOW-07)."""
    attachments: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for edge in subject_node.edges:
        target_id = edge.to_id.upper()
        if target_id in seen_ids:
            continue
        target = store.get_node(target_id)
        if not target or (target.type != "artifact" and not target.id.startswith("ART-") and "path" not in target.attrs):
            continue

        seen_ids.add(target_id)
        fpath_rel = str(target.attrs.get("path", "")).strip() or str(target.attrs.get("rendered_file", "")).strip()
        fname = str(target.attrs.get("file_name", "")).strip() or (Path(fpath_rel).name if fpath_rel else target.id)
        ext = Path(fname).suffix.lower()
        is_text = ext in TEXT_EXTENSIONS
        content = _read_attachment_text(vault_dir, fpath_rel, is_text)

        attachments.append({
            "id": target.id, "title": target.title, "file_name": fname, "path": fpath_rel,
            "relation": edge.relation, "is_text": is_text, "extension": ext.lstrip("."), "content": content,
        })
    return attachments


def resolve_subject_linked_notes(
    subject_node: Node,
    store: StoreProtocol,
) -> list[dict[str, Any]]:
    """Resolve linked child ideas, observations, questions, and frictions (WORKFLOW-07)."""
    notes: list[dict[str, Any]] = []
    seen_ids: set[str] = {subject_node.id.upper()}

    for edge in subject_node.edges:
        target_id = edge.to_id.upper()
        if target_id in seen_ids:
            continue
        target = store.get_node(target_id)
        if not target:
            continue
        is_art = target.type == "artifact" or target.id.startswith("ART-") or "path" in target.attrs
        if is_art:
            continue

        seen_ids.add(target_id)
        raw_body = target.body.strip() if target.body else ""
        excerpt = (raw_body[:240] + "...") if len(raw_body) > 240 else raw_body
        notes.append({
            "id": target.id,
            "type": target.type,
            "title": target.title,
            "relation": edge.relation,
            "body_excerpt": excerpt,
        })
    return notes


def format_attachments_markdown(attachments: list[dict[str, Any]]) -> str:
    """Format attached files as embedded text codeblocks or media references (WORKFLOW-07)."""
    if not attachments:
        return ""

    lines: list[str] = ["### Attached Reference Files & Deliverables\n"]
    for art in attachments:
        fname = art["file_name"]
        art_id = art["id"]
        rel = art["relation"]
        if art["is_text"] and art["content"]:
            ext = art["extension"] or "text"
            lines.append(f"#### File: `{fname}` (Node: {art_id}, Relation: {rel})\n```{ext}\n{art['content']}\n```\n")
        else:
            path_str = art["path"] or fname
            lines.append(f"- **Attached File**: `{fname}` (`{path_str}`) [Node: {art_id}, Relation: {rel}]\n")
    return "\n".join(lines) + "\n"


def format_linked_notes_markdown(notes: list[dict[str, Any]]) -> str:
    """Format linked notes into a concise bullet list with excerpts (WORKFLOW-07)."""
    if not notes:
        return ""

    lines: list[str] = ["### Linked Notes & Context\n"]
    for n in notes:
        desc = f" > {n['body_excerpt']}" if n["body_excerpt"] else " *(No description)*"
        lines.append(f"- **[{n['id']}] {n['title']}** ({n['type']} · relation: `{n['relation']}`)\n{desc}\n")
    return "\n".join(lines) + "\n"


def stage_subject_files_to_unit(
    unit_id: str,
    subject_nodes: list[Node],
    store: StoreProtocol,
    vault_dir: Path,
) -> list[str]:
    """Copy subject attached files into unit work folder for agent tool access (MCP-01)."""
    unit_folder = vault_dir / "work" / unit_id.strip().upper()
    unit_folder.mkdir(parents=True, exist_ok=True)
    staged_names: list[str] = []

    for subj in subject_nodes:
        attachments = resolve_subject_attachments(subj, store, vault_dir=vault_dir)
        for art in attachments:
            rel_path = art.get("path")
            fname = art.get("file_name")
            if not rel_path or not fname:
                continue
            src = vault_dir / rel_path
            dst = unit_folder / fname
            if src.exists() and src.is_file() and not dst.exists():
                try:
                    shutil.copy2(src, dst)
                    staged_names.append(fname)
                except Exception:
                    pass
    return staged_names
