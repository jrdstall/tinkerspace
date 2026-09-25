"""Attachment and linked note web view action handlers.

Layer 4 Web surface module governed by INTAKE-05 and INTAKE-06.
"""

from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any
from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from iw.contracts.models import Author, AuthorKind, Edge, Node
from iw.contracts.store import StoreProtocol

TYPE_PREFIXES: dict[str, str] = {
    "idea": "IDEA",
    "observation": "OBS",
    "friction": "FRI",
    "question": "QUE",
    "source": "SRC",
    "asset": "AST",
    "artifact": "ART",
    "experiment": "EXP",
}
IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}


async def _save_attachment_file(form: Any, node_id: str, vault_dir: Path) -> tuple[str, str] | None:
    """Extract uploaded or drop file and persist into vault attachments folder (INTAKE-05)."""
    upload = form.get("file")
    drop_name = str(form.get("drop_file", "")).strip()
    target_folder = vault_dir / "attachments" / node_id
    target_folder.mkdir(parents=True, exist_ok=True)

    if isinstance(upload, UploadFile) and upload.filename:
        safe_name = Path(upload.filename).name
        target_path = target_folder / safe_name
        content = await upload.read()
        target_path.write_bytes(content)
        return safe_name, f"attachments/{node_id}/{safe_name}"

    if drop_name:
        safe_name = Path(drop_name).name
        src = vault_dir / "drop" / safe_name
        if src.exists() and src.is_file():
            target_path = target_folder / safe_name
            shutil.move(str(src), str(target_path))
            return safe_name, f"attachments/{node_id}/{safe_name}"

    return None


def _create_art_node(
    store: StoreProtocol, node: Node, safe_name: str, rel_path: str,
    title: str, note: str, now: datetime, author: Author,
) -> str:
    """Create and write an ART node for an attachment (INTAKE-05)."""
    art_id = store.allocate_id("ART")
    art_node = Node(
        id=art_id, type="artifact", title=title, created=now, domain=node.domain,
        tags=["attachment"], body=note or f"Attached file: `{rel_path}`",
        edges=[Edge(from_id=art_id, to_id=node.id, relation="attached_to", created=now, author=author)],
        attrs={"file_name": safe_name, "path": rel_path, "attached_to": node.id},
    )
    store.write_node(art_node, author=author)
    return art_id


async def node_attach_file_action(request: Request) -> Response:
    """Handle direct file upload or drop attachment to a subject node (INTAKE-05)."""
    store: StoreProtocol = request.app.state.store
    node_id = request.path_params.get("node_id", "").strip().upper()
    node = store.get_node(node_id)
    if not node:
        return RedirectResponse(url="/", status_code=303)

    vault_dir = getattr(store, "vault_dir", Path("."))
    form = await request.form()
    saved = await _save_attachment_file(form, node_id, vault_dir)
    if not saved:
        return RedirectResponse(url=f"/node/{node_id}", status_code=303)

    safe_name, rel_path = saved
    title = str(form.get("title", "")).strip() or safe_name
    relation = str(form.get("relation", "evidence_for")).strip() or "evidence_for"
    note = str(form.get("note", "")).strip()
    set_cg = form.get("set_concept_graphic") is not None

    now = datetime.now(timezone.utc)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    art_id = _create_art_node(store, node, safe_name, rel_path, title, note, now, author)

    node.edges.append(Edge(from_id=node.id, to_id=art_id, relation=relation, created=now, author=author, note=safe_name))
    if set_cg and Path(safe_name).suffix.lower() in IMAGE_EXTENSIONS:
        node.attrs["concept_graphic"] = rel_path
    node.last_touched = now
    store.write_node(node, author=author)

    event_log = getattr(store, "event_log", None)
    if event_log:
        event_log.append(kind="attachment.added", subject_id=node.id, author=author, payload={"file": safe_name, "art_id": art_id})

    from_p = request.query_params.get("from", "").strip()
    return RedirectResponse(url=f"/node/{node_id}?from={from_p}" if from_p else f"/node/{node_id}", status_code=303)


def _build_and_save_child(
    store: StoreProtocol, node: Node, child_type: str,
    title: str, body: str, tags: list[str], now: datetime, author: Author,
) -> Node:
    """Instantiate and write a child note linked to parent node (INTAKE-06)."""
    prefix = TYPE_PREFIXES.get(child_type, "OBS")
    new_id = store.allocate_id(prefix)
    child = Node(
        id=new_id, type=child_type, title=title, created=now, domain=node.domain,
        tags=tags, body=body, state="active",
        edges=[Edge(from_id=new_id, to_id=node.id, relation="questions" if child_type == "question" else "relates_to", created=now, author=author)],
        attrs={},
    )
    return store.write_node(child, author=author)


async def node_capture_linked_action(request: Request) -> Response:
    """Capture child idea, observation, friction, or question linked to node (INTAKE-06)."""
    store: StoreProtocol = request.app.state.store
    node_id = request.path_params.get("node_id", "").strip().upper()
    node = store.get_node(node_id)
    if not node:
        return RedirectResponse(url="/", status_code=303)

    form = await request.form()
    child_type = str(form.get("type", "observation")).strip().lower()
    title = str(form.get("title", "")).strip() or f"Untitled {child_type.capitalize()}"
    relation = str(form.get("relation", "relates_to")).strip() or "relates_to"
    body = str(form.get("body", "")).strip()
    raw_tags = str(form.get("tags", "")).strip()
    tags = [t.strip().lstrip("#") for t in raw_tags.split(",") if t.strip()] if raw_tags else list(node.tags)

    now = datetime.now(timezone.utc)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    child_node = _build_and_save_child(store, node, child_type, title, body, tags, now, author)

    node.edges.append(Edge(from_id=node.id, to_id=child_node.id, relation=relation, created=now, author=author, note=child_node.title))
    node.last_touched = now
    store.write_node(node, author=author)

    event_log = getattr(store, "event_log", None)
    if event_log:
        event_log.append(kind="linked_note.captured", subject_id=node.id, author=author, payload={"child_id": child_node.id, "type": child_type})

    from_p = request.query_params.get("from", "").strip()
    return RedirectResponse(url=f"/node/{node_id}?from={from_p}" if from_p else f"/node/{node_id}", status_code=303)
