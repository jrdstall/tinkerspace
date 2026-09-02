"""Behaviour tests for keyboard triage and inbox item conversion.

Traces TRIAGE-01 through TRIAGE-04 per docs/design/specs/TRIAGE.md.
"""

from datetime import datetime, timezone
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Edge, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.core.triage import TriageService
from iw.web.app import create_app


def test_triage_01_converts_inbox_item_into_node_with_author_stamped(tmp_path: Path):
    """TRIAGE-01: Triage assigns deterministic ID, stamps author, saves node, and removes inbox item."""
    event_log = FileEventLog(log_path=tmp_path / "events.jsonl")
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log)
    service = TriageService(store=store)

    inbox_item = store.append_inbox("Bike computer screen unreadable in direct sunlight")
    assert len(service.list_inbox_items()) == 1

    node_draft = Node(
        id="",
        type="friction",
        title="Bike computer screen unreadable in sunlight",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["cycling", "display"],
        state="active",
        body=inbox_item.raw_text,
    )
    author = Author(kind=AuthorKind.HUMAN, courier="triage-surface")

    saved_node = service.triage_item(item_id=inbox_item.id, node=node_draft, author=author)

    assert saved_node.id == "FRI-A01"
    assert saved_node.type == "friction"
    assert saved_node.title == "Bike computer screen unreadable in sunlight"
    assert saved_node.domain == "hardware"
    assert "cycling" in saved_node.tags

    # Inbox item removed
    assert len(service.list_inbox_items()) == 0

    # Node exists in store
    fetched = store.get_node("FRI-A01")
    assert fetched is not None
    assert fetched.id == "FRI-A01"


def test_triage_02_creates_candidate_edge_links(tmp_path: Path):
    """TRIAGE-02: Triage can attach directed edges to existing nodes during conversion."""
    store = MarkdownStore(vault_dir=tmp_path)
    service = TriageService(store=store)

    # Pre-existing friction node
    author = Author(kind=AuthorKind.HUMAN, courier="triage-surface")
    fri_node = Node(
        id="FRI-A01",
        type="friction",
        title="Bike computer screen unreadable",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["cycling"],
        state="active",
    )
    store.write_node(fri_node, author=author)

    inbox_item = store.append_inbox("Use memory-in-pixel display with sunlight reflective layer")

    idea_draft = Node(
        id="",
        type="idea",
        title="Memory-in-pixel display for bike computer",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["display", "low-power"],
        state="active",
        edges=[
            Edge(
                from_id="",
                to_id="FRI-A01",
                relation="addresses",
                created=datetime.now(timezone.utc),
                author=author,
            )
        ],
        body=inbox_item.raw_text,
    )

    saved_idea = service.triage_item(item_id=inbox_item.id, node=idea_draft, author=author)
    assert saved_idea.id == "IDEA-A01"
    assert len(saved_idea.edges) == 1
    assert saved_idea.edges[0].from_id == "IDEA-A01"
    assert saved_idea.edges[0].to_id == "FRI-A01"
    assert saved_idea.edges[0].relation == "addresses"


def test_triage_03_discard_removes_inbox_item_without_creating_node(tmp_path: Path):
    """TRIAGE-03: Discarding an inbox item deletes it from disk without creating a mature node."""
    store = MarkdownStore(vault_dir=tmp_path)
    service = TriageService(store=store)

    inbox_item = store.append_inbox("Spam or random junk note")
    assert len(service.list_inbox_items()) == 1

    deleted = service.discard_item(inbox_item.id)
    assert deleted is True
    assert len(service.list_inbox_items()) == 0
    assert len(store.list_nodes()) == 0


def test_triage_04_web_triage_flow_and_empty_state(tmp_path: Path):
    """TRIAGE-04: Web triage interface renders active item, handles accept/discard, and shows inbox zero."""
    store = MarkdownStore(vault_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    # 1. Empty state
    res_empty = client.get("/triage")
    assert res_empty.status_code == 200
    assert "Inbox Zero!" in res_empty.text

    # 2. Add an inbox item
    item = store.append_inbox("Chain cleaning takes too long and makes a mess")

    # 3. View triage surface with item
    res_item = client.get("/triage")
    assert res_item.status_code == 200
    assert "Keyboard Triage Pass" in res_item.text
    assert "Chain cleaning takes too long" in res_item.text

    # 4. Accept item via form POST
    res_accept = client.post(
        "/triage/accept",
        data={
            "item_id": item.id,
            "node_type": "friction",
            "title": "Messy chain cleaning process",
            "domain": "maintenance",
            "tags": "bike, cleaning",
            "body": item.raw_text,
            "edge_target": "",
            "edge_rel": "",
        },
        follow_redirects=True,
    )
    assert res_accept.status_code == 200
    assert "Inbox Zero!" in res_accept.text

    # 5. Verify created node in store
    node = store.get_node("FRI-A01")
    assert node is not None
    assert node.title == "Messy chain cleaning process"
    assert node.domain == "maintenance"


def test_triage_05_web_triage_editable_body_and_node_datalist(tmp_path: Path):
    """TRIAGE-02 & TRIAGE-04: Web triage allows editing raw thought text and linking with datalist formatted IDs."""
    store = MarkdownStore(vault_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)
    author = Author(kind=AuthorKind.HUMAN, courier="test")

    # Pre-create target friction node
    fri_node = Node(
        id="FRI-A01",
        type="friction",
        title="Bike computer screen unreadable",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["cycling"],
        state="active",
    )
    store.write_node(fri_node, author=author)

    # Inbox item with typos
    item = store.append_inbox("byke compooter unredable in sunlite")

    # GET triage view - verify editable textarea and datalist options
    res_get = client.get("/triage")
    assert res_get.status_code == 200
    assert "Captured Thought &amp; Note Body (Editable)" in res_get.text or "Captured Thought & Note Body (Editable)" in res_get.text
    assert "FRI-A01" in res_get.text
    assert "existing-nodes-list" in res_get.text

    # Submit with edited body and datalist-formatted target node
    res_post = client.post(
        "/triage/accept",
        data={
            "item_id": item.id,
            "node_type": "idea",
            "title": "Sunlight Readable Bike Display",
            "domain": "hardware",
            "tags": "cycling, display",
            "body": "Fixed typo: Bike computer display with transflective memory layer.",
            "edge_target": "FRI-A01 — Bike computer screen unreadable (friction)",
            "edge_rel": "addresses",
        },
        follow_redirects=True,
    )
    assert res_post.status_code == 200

    saved_idea = store.get_node("IDEA-A01")
    assert saved_idea is not None
    assert saved_idea.body == "Fixed typo: Bike computer display with transflective memory layer."
    assert len(saved_idea.edges) == 1
    assert saved_idea.edges[0].to_id == "FRI-A01"
    assert saved_idea.edges[0].relation == "addresses"

