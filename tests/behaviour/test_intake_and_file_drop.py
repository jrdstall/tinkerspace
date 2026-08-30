"""Behaviour tests for Intake and File Drop workflow.

Traces INTAKE-01 through INTAKE-04 per docs/design/specs/INTAKE.md.
"""

from datetime import datetime, timezone
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.store import MarkdownStore
from iw.web.app import create_app


def test_intake_01_dropped_file_in_vault_drop_is_discovered_on_request(tmp_path: Path):
    """INTAKE-01: Exported sketches arriving via sync in drop/ are discovered on request."""
    store = MarkdownStore(vault_dir=tmp_path)
    drop_dir = tmp_path / "drop"
    drop_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initially drop is empty
    assert store.list_dropped_files() == []

    # 2. File arrives via tablet sync
    sketch_file = drop_dir / "2026-08-29-puck-schematic.png"
    sketch_file.write_bytes(b"\x89PNG\r\n\x1a\nfake-image-bytes")

    pdf_file = drop_dir / "nrf52840-datasheet.pdf"
    pdf_file.write_text("PDF content placeholder")

    # 3. Discovered on read without watchers
    dropped = store.list_dropped_files()
    assert len(dropped) == 2
    assert [p.name for p in dropped] == ["2026-08-29-puck-schematic.png", "nrf52840-datasheet.pdf"]


def test_intake_02_creates_stub_node_with_attached_file_and_embed(tmp_path: Path):
    """INTAKE-02: Creating a stub node attaches the dropped file and sets markdown embed."""
    store = MarkdownStore(vault_dir=tmp_path)
    drop_dir = tmp_path / "drop"
    drop_dir.mkdir(parents=True, exist_ok=True)

    sketch_file = drop_dir / "handlebar-sketch.png"
    sketch_file.write_bytes(b"\x89PNGfake")

    author = Author(kind=AuthorKind.HUMAN, courier="intake-surface")
    draft = Node(
        id="",
        type="artifact",
        title="Handlebar Puck Block Diagram",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["tablet", "sketch", "ble"],
        state="active",
    )

    saved = store.intake_file(file_name="handlebar-sketch.png", node=draft, author=author)
    assert saved.id == "ART-A01"
    assert saved.type == "artifact"
    assert saved.attrs.get("rendered_file") == "drop/handlebar-sketch.png"
    assert "![Handlebar Puck Block Diagram](drop/handlebar-sketch.png)" in saved.body

    # Verify written to disk and readable
    reloaded = store.get_node("ART-A01")
    assert reloaded is not None
    assert reloaded.id == "ART-A01"
    assert reloaded.attrs.get("rendered_file") == "drop/handlebar-sketch.png"


def test_intake_03_attaches_dropped_file_to_existing_node(tmp_path: Path):
    """INTAKE-03: Attaching dropped file to existing mature node updates its markdown body."""
    store = MarkdownStore(vault_dir=tmp_path)
    drop_dir = tmp_path / "drop"
    drop_dir.mkdir(parents=True, exist_ok=True)

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    node = Node(
        id="IDEA-A01",
        type="idea",
        title="BLE Display Puck",
        created=datetime.now(timezone.utc),
        domain="cycling",
        tags=["hardware"],
        state="active",
        body="Initial concept notes for display puck.",
    )
    store.write_node(node, author=author)

    pdf_file = drop_dir / "display-datasheet.pdf"
    pdf_file.write_text("datasheet content")

    intake_author = Author(kind=AuthorKind.HUMAN, courier="intake-surface")
    updated = store.intake_manager.attach_file_to_node(
        file_name="display-datasheet.pdf",
        target_node_id="IDEA-A01",
        author=intake_author,
    )
    assert updated is not None
    assert "display-datasheet.pdf" in updated.body
    assert "[display-datasheet.pdf](drop/display-datasheet.pdf)" in updated.body
    assert "Initial concept notes for display puck." in updated.body


def test_intake_04_web_intake_flow_and_empty_state(tmp_path: Path):
    """INTAKE-04: Web intake views support browsing dropped items, stub creation, and attaching."""
    store = MarkdownStore(vault_dir=tmp_path)
    drop_dir = tmp_path / "drop"
    drop_dir.mkdir(parents=True, exist_ok=True)

    app = create_app(store=store)
    client = TestClient(app)

    # 1. Empty state
    res_empty = client.get("/intake")
    assert res_empty.status_code == 200
    assert "Drop Folder is Empty" in res_empty.text

    # 2. Add dropped file
    (drop_dir / "trail-cam-diagram.svg").write_text("<svg>diagram</svg>")

    res_item = client.get("/intake")
    assert res_item.status_code == 200
    assert "trail-cam-diagram.svg" in res_item.text

    # 3. Create stub node via POST /intake/create
    create_res = client.post(
        "/intake/create",
        data={
            "file_name": "trail-cam-diagram.svg",
            "node_type": "artifact",
            "title": "Trail Camera Wiring Diagram",
            "domain": "auto",
            "tags": "jeep, video",
            "body": "",
        },
        follow_redirects=True,
    )
    assert create_res.status_code == 200
    assert "ART-A01" in create_res.text
    assert "Trail Camera Wiring Diagram" in create_res.text
