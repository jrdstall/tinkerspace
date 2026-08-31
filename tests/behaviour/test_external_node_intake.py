"""Behaviour tests for External Node Intake and Foreign ID Routing.

Traces EXTINT-01 through EXTINT-05 per docs/design/specs/EXTINT.md.
"""

from datetime import datetime, timezone
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Edge, Node
from iw.core.store import MarkdownStore
from iw.domain.intake.external import ingest_external_bundle, ingest_external_node
from iw.web.app import create_app


def _sample_local_node(node_id: str = "IDEA-A01") -> Node:
    return Node(
        id=node_id,
        type="idea",
        title="Local Handlebar Display",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["display", "local"],
        body="Original local note content.",
    )


def test_extint_01_ingests_external_markdown_as_typed_node(tmp_path: Path):
    """EXTINT-01: Ingests external markdown text and imports it into the local vault as a typed node."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    raw_note = (
        "---\n"
        "id: FRI-B01\n"
        "type: friction\n"
        "title: Sunlight glare obscures screen during mid-day rides\n"
        "domain: optics\n"
        "tags: [glare, sunlight]\n"
        "---\n"
        "# Problem Context\n"
        "Riders cannot read map at noon."
    )

    imported = ingest_external_node(
        store=store,
        raw_text=raw_note,
        source_vault="external-research",
        author=author,
    )

    assert imported is not None
    assert imported.id == "FRI-B01"
    assert imported.type == "friction"
    assert "Sunlight glare" in imported.title
    assert "Riders cannot read map" in imported.body

    # Check store persistence
    reloaded = store.get_node("FRI-B01")
    assert reloaded is not None
    assert reloaded.title == imported.title


def test_extint_02_preserves_non_colliding_source_id(tmp_path: Path):
    """EXTINT-02: Non-colliding source IDs are preserved intact without re-allocation."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    raw_note = (
        "---\n"
        "id: OBS-X99\n"
        "type: observation\n"
        "title: OLED consumes 80mA white screen\n"
        "domain: power\n"
        "tags: [power]\n"
        "---\n"
        "Measured on bench."
    )

    imported = ingest_external_node(
        store=store,
        raw_text=raw_note,
        source_vault="lab-bench",
        author=author,
    )

    assert imported.id == "OBS-X99"
    assert store.get_node("OBS-X99") is not None


def test_extint_03_allocates_new_id_on_collision_and_records_foreign_id(tmp_path: Path):
    """EXTINT-03: Colliding source IDs allocate the next local sequential ID and preserve foreign ID."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    # Local pre-existing IDEA-A01
    local_idea = _sample_local_node("IDEA-A01")
    store.write_node(local_idea, author=author)

    # Incoming foreign note ALSO named IDEA-A01
    foreign_note = (
        "---\n"
        "id: IDEA-A01\n"
        "type: idea\n"
        "title: Foreign Idea with Colliding ID\n"
        "domain: software\n"
        "tags: [foreign]\n"
        "---\n"
        "This is an idea from another vault."
    )

    imported = ingest_external_node(
        store=store,
        raw_text=foreign_note,
        source_vault="work-laptop",
        author=author,
    )

    # Must allocate next local sequence ID
    assert imported.id == "IDEA-A02"
    assert imported.attrs.get("foreign_id") == "IDEA-A01"

    # Original local note remains intact
    orig_local = store.get_node("IDEA-A01")
    assert orig_local is not None
    assert orig_local.title == "Local Handlebar Display"


def test_extint_04_appends_source_vault_tag(tmp_path: Path):
    """EXTINT-04: Ingestion automatically appends the foreign vault tag vault:<source_name>."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    raw_note = (
        "---\n"
        "id: AST-A01\n"
        "type: asset\n"
        "title: Sharp Memory LCD Datasheet\n"
        "domain: hardware\n"
        "tags: [datasheet, display]\n"
        "---\n"
        "Datasheet specs."
    )

    imported = ingest_external_node(
        store=store,
        raw_text=raw_note,
        source_vault="component-vault",
        author=author,
    )

    assert "vault:component-vault" in imported.tags
    assert "datasheet" in imported.tags
    assert "display" in imported.tags


def test_extint_05_remaps_bundle_edges_when_ids_are_reallocated(tmp_path: Path):
    """EXTINT-05: Ingestion remaps inter-note edge references when colliding IDs are remapped."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    # Local pre-existing IDEA-A01 and ART-A01
    store.write_node(_sample_local_node("IDEA-A01"), author=author)
    art_local = Node(
        id="ART-A01",
        type="artifact",
        title="Local Artifact",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["local"],
    )
    store.write_node(art_local, author=author)

    # Foreign bundle where foreign IDEA-A01 links to foreign ART-A01
    foreign_idea_text = (
        "---\n"
        "id: IDEA-A01\n"
        "type: idea\n"
        "title: Foreign Idea Linking to Foreign Artifact\n"
        "domain: hardware\n"
        "tags: [bundle]\n"
        "edges:\n"
        "  - { from: IDEA-A01, to: ART-A01, relation: illustrates, note: 'Optical stack diagram' }\n"
        "---\n"
        "Idea body linking to art."
    )
    foreign_art_text = (
        "---\n"
        "id: ART-A01\n"
        "type: artifact\n"
        "title: Foreign Optical Stack Diagram\n"
        "domain: hardware\n"
        "tags: [bundle]\n"
        "---\n"
        "Artifact body."
    )

    files = [
        ("idea.md", foreign_idea_text),
        ("optical-stack.md", foreign_art_text),
    ]

    imported_nodes = ingest_external_bundle(
        store=store,
        files=files,
        source_vault="external-lab",
        author=author,
    )

    assert len(imported_nodes) == 2
    idea_node = next(n for n in imported_nodes if n.type == "idea")
    art_node = next(n for n in imported_nodes if n.type == "artifact")

    # Collisions reallocated IDs to IDEA-A02 and ART-A02
    assert idea_node.id == "IDEA-A02"
    assert art_node.id == "ART-A02"

    # Edge from IDEA-A02 must point to remapped ART-A02 (NOT local ART-A01)
    assert len(idea_node.edges) == 1
    edge = idea_node.edges[0]
    assert edge.from_id == "IDEA-A02"
    assert edge.to_id == "ART-A02"
    assert edge.relation == "illustrates"
