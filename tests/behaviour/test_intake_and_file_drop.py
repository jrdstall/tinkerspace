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
    assert store.list_dropped_files() == []

    sketch_file = drop_dir / "2026-08-29-puck-schematic.png"
    sketch_file.write_bytes(b"\x89PNG\r\n\x1a\nfake-image-bytes")
    pdf_file = drop_dir / "nrf52840-datasheet.pdf"
    pdf_file.write_text("PDF content placeholder")

    dropped = store.list_dropped_files()
    assert len(dropped) == 2
    assert [p.name for p in dropped] == ["2026-08-29-puck-schematic.png", "nrf52840-datasheet.pdf"]


def test_intake_02_creates_stub_node_with_attached_file_and_embed(tmp_path: Path):
    """INTAKE-02: Creating a stub node moves dropped file to attachments/{node_id}/ and sets embed."""
    store = MarkdownStore(vault_dir=tmp_path)
    drop_dir = tmp_path / "drop"
    drop_dir.mkdir(parents=True, exist_ok=True)

    sketch_file = drop_dir / "handlebar-sketch.png"
    sketch_file.write_bytes(b"\x89PNGfake")

    author = Author(kind=AuthorKind.HUMAN, courier="intake-surface")
    draft = Node(
        id="", type="artifact", title="Handlebar Puck Block Diagram",
        created=datetime.now(timezone.utc), domain="hardware",
        tags=["tablet", "sketch", "ble"], state="active",
    )

    saved = store.intake_file(file_name="handlebar-sketch.png", node=draft, author=author)
    expected_rel = f"attachments/{saved.id}/handlebar-sketch.png"
    assert saved.id == "ART-A01"
    assert saved.type == "artifact"
    assert saved.attrs.get("rendered_file") == expected_rel
    assert f"![Handlebar Puck Block Diagram]({expected_rel})" in saved.body

    # Verify moved from drop to attachments and readable on reload
    assert not sketch_file.exists()
    assert (tmp_path / expected_rel).exists()
    reloaded = store.get_node("ART-A01")
    assert reloaded is not None
    assert reloaded.attrs.get("rendered_file") == expected_rel


def test_intake_03_attaches_dropped_file_to_existing_node(tmp_path: Path):
    """INTAKE-03: Attaching dropped file moves file to attachments/{node_id}/ and updates body."""
    store = MarkdownStore(vault_dir=tmp_path)
    drop_dir = tmp_path / "drop"
    drop_dir.mkdir(parents=True, exist_ok=True)

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    node = Node(
        id="IDEA-A01", type="idea", title="BLE Display Puck",
        created=datetime.now(timezone.utc), domain="cycling",
        tags=["hardware"], state="active", body="Initial concept notes for display puck.",
    )
    store.write_node(node, author=author)

    pdf_file = drop_dir / "display-datasheet.pdf"
    pdf_file.write_text("datasheet content")

    intake_author = Author(kind=AuthorKind.HUMAN, courier="intake-surface")
    updated = store.intake_manager.attach_file_to_node(
        file_name="display-datasheet.pdf", target_node_id="IDEA-A01", author=intake_author,
    )
    expected_rel = "attachments/IDEA-A01/display-datasheet.pdf"
    assert updated is not None
    assert "display-datasheet.pdf" in updated.body
    assert f"[display-datasheet.pdf]({expected_rel})" in updated.body
    assert "Initial concept notes for display puck." in updated.body
    assert not pdf_file.exists()
    assert (tmp_path / expected_rel).exists()


def test_intake_04_web_intake_flow_and_empty_state(tmp_path: Path):
    """INTAKE-04: Web intake views support browsing dropped items, stub creation, and attaching."""
    store = MarkdownStore(vault_dir=tmp_path)
    drop_dir = tmp_path / "drop"
    drop_dir.mkdir(parents=True, exist_ok=True)

    app = create_app(store=store)
    client = TestClient(app)

    res_empty = client.get("/intake")
    assert res_empty.status_code == 200
    assert "Drop Folder is Empty" in res_empty.text

    (drop_dir / "trail-cam-diagram.svg").write_text("<svg>diagram</svg>")
    res_item = client.get("/intake")
    assert res_item.status_code == 200
    assert "trail-cam-diagram.svg" in res_item.text

    create_res = client.post(
        "/intake/create",
        data={"file_name": "trail-cam-diagram.svg", "node_type": "artifact", "title": "Trail Camera Wiring Diagram", "domain": "auto", "tags": "jeep", "body": ""},
        follow_redirects=True,
    )
    assert create_res.status_code == 200
    assert "ART-A01" in create_res.text
    assert not (drop_dir / "trail-cam-diagram.svg").exists()
    assert (tmp_path / "attachments" / "ART-A01" / "trail-cam-diagram.svg").exists()
    assert "Drop Folder is Empty" in client.get("/intake").text

    (drop_dir / "stray.txt").write_text("delete me")
    discard_res = client.post("/intake/discard", data={"file_name": "stray.txt"}, follow_redirects=True)
    assert discard_res.status_code == 200
    assert not (drop_dir / "stray.txt").exists()
    assert "Drop Folder is Empty" in discard_res.text


def test_intake_05_legacy_inbox_drop_migration_and_auto_mkdir(tmp_path: Path):
    """INTAKE-01: Auto-creates drop/ and cleans up legacy inbox/drop/ on scan."""
    inbox_drop = tmp_path / "inbox" / "drop"
    inbox_drop.mkdir(parents=True, exist_ok=True)
    stray_file = inbox_drop / "cognitive-c2-network.md"
    stray_file.write_text("# Cognitive C2 Network\nNotes on mesh topology.")

    store = MarkdownStore(vault_dir=tmp_path)
    dropped = store.list_dropped_files()
    assert (tmp_path / "drop").is_dir()
    assert len(dropped) == 1
    assert dropped[0].name == "cognitive-c2-network.md"
    assert (tmp_path / "drop" / "cognitive-c2-network.md").exists()
    assert not inbox_drop.exists()


def test_intake_06_markdown_dropped_file_populates_body(tmp_path: Path):
    """INTAKE-02: Dropped markdown file imports text and moves to attachments/{node_id}/."""
    store = MarkdownStore(vault_dir=tmp_path)
    drop_dir = tmp_path / "drop"
    drop_dir.mkdir(parents=True, exist_ok=True)
    doc = drop_dir / "sensor-mesh.md"
    doc.write_text("# Sensor Mesh Architecture\nDistributed sensor fabric for field telemetry.")

    author = Author(kind=AuthorKind.HUMAN, courier="intake-surface")
    draft = Node(
        id="", type="idea", title="Sensor Mesh", created=datetime.now(timezone.utc),
        domain="sensing", tags=["mesh", "telemetry"], state="active",
    )
    saved = store.intake_file(file_name="sensor-mesh.md", node=draft, author=author)
    expected_rel = f"attachments/{saved.id}/sensor-mesh.md"
    assert saved.attrs.get("rendered_file") == expected_rel
    assert "Distributed sensor fabric for field telemetry." in saved.body
    assert f"[sensor-mesh.md]({expected_rel})" in saved.body
    assert not doc.exists()
    assert (tmp_path / expected_rel).exists()


def test_intake_07_node_detail_renders_attached_document_reader(tmp_path: Path):
    """INTAKE-04: Node detail view renders attached document reader card for readable files."""
    store = MarkdownStore(vault_dir=tmp_path)
    drop_dir = tmp_path / "drop"
    drop_dir.mkdir(parents=True, exist_ok=True)
    doc = drop_dir / "notes.txt"
    doc.write_text("Crucial telemetry calibration details line 1\nline 2")

    author = Author(kind=AuthorKind.HUMAN, courier="test")
    node = Node(
        id="IDEA-A01", type="idea", title="Test Idea", created=datetime.now(timezone.utc),
        domain="general", tags=[], state="active", body="Some body text.",
        attrs={"rendered_file": "drop/notes.txt"},
    )
    store.write_node(node, author=author)

    app = create_app(store=store)
    client = TestClient(app)
    res = client.get("/node/IDEA-A01")
    assert res.status_code == 200
    assert "Attached Reference Documents" in res.text
    assert "notes.txt" in res.text
    assert "Crucial telemetry calibration details line 1" in res.text
    assert "/vault-file/drop/notes.txt" in res.text


