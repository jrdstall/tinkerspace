"""Behaviour tests for interactive node search picker in Triage and Explore.

Traces TRIAGE-07 and EXPLORE-09 per docs/design/specs.
"""

from datetime import datetime, timezone
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Edge, Node
from iw.core.events import FileEventLog
from iw.core.index import InMemoryIndex
from iw.core.store import MarkdownStore
from iw.web.app import create_app


def _sample_nodes() -> list[Node]:
    now = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    return [
        Node(
            id="FRI-A01",
            type="friction",
            title="Bike computer screens washed out in sunlight",
            created=now,
            domain="cycling",
            tags=["hardware", "optics"],
            state="active",
            author=author,
            body="Existing LCD head units are completely illegible under midday glare.",
            attrs={"keywords": ["transflective", "sunlight"]},
        ),
        Node(
            id="IDEA-A01",
            type="idea",
            title="Memory-in-pixel handlebar puck display",
            created=now,
            domain="cycling",
            tags=["hardware", "low-power"],
            state="active",
            author=author,
            body="Reflective Sharp memory LCD consumes microwatts and has infinite contrast.",
            attrs={"keywords": ["chameleon", "display"], "cml": 2},
        ),
        Node(
            id="OBS-A01",
            type="observation",
            title="E-ink price drops on flexible substrates",
            created=now,
            domain="electronics",
            tags=["manufacturing"],
            state="active",
            author=author,
            body="Flexible epaper displays now cost under three dollars in quantity.",
            attrs={"keywords": ["plastic", "epaper"]},
        ),
    ]


def test_triage_07_and_explore_09_search_for_picker_multi_field_matches() -> None:
    """TRIAGE-07, EXPLORE-09: Search finds nodes by ID, title, tag, keyword, or body."""
    nodes = _sample_nodes()
    index = InMemoryIndex(nodes)

    by_id = index.search_for_picker(query="FRI-A01")
    assert len(by_id) == 1
    assert by_id[0]["id"] == "FRI-A01"

    by_title = index.search_for_picker(query="handlebar")
    assert len(by_title) == 1
    assert by_title[0]["id"] == "IDEA-A01"

    by_tag = index.search_for_picker(query="optics")
    assert len(by_tag) == 1
    assert by_tag[0]["id"] == "FRI-A01"

    by_kw = index.search_for_picker(query="chameleon")
    assert len(by_kw) == 1
    assert by_kw[0]["id"] == "IDEA-A01"

    by_body = index.search_for_picker(query="microwatts")
    assert len(by_body) == 1
    assert by_body[0]["id"] == "IDEA-A01"
    assert "microwatts" in by_body[0]["excerpt"]


def test_triage_07_and_explore_09_search_for_picker_excludes_source_node() -> None:
    """TRIAGE-07, EXPLORE-09: Exclude filter successfully omits candidate node."""
    nodes = _sample_nodes()
    index = InMemoryIndex(nodes)

    matches = index.search_for_picker(query="cycling", exclude_id="FRI-A01")
    matched_ids = [m["id"] for m in matches]
    assert "FRI-A01" not in matched_ids
    assert "IDEA-A01" in matched_ids


def test_triage_07_and_explore_09_api_endpoint(tmp_path: Path) -> None:
    """TRIAGE-07, EXPLORE-09: /api/nodes/search endpoint returns structured suggestions."""
    event_log = FileEventLog(log_path=tmp_path / "events.jsonl")
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log)
    for n in _sample_nodes():
        store.write_node(n, author=n.author)

    app = create_app(store=store)
    client = TestClient(app)

    res = client.get("/api/nodes/search?q=cycling")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2
    assert any(d["id"] == "FRI-A01" for d in data)

    res_ex = client.get("/api/nodes/search?q=cycling&exclude=FRI-A01")
    assert res_ex.status_code == 200
    data_ex = res_ex.json()
    assert not any(d["id"] == "FRI-A01" for d in data_ex)
    assert any(d["id"] == "IDEA-A01" for d in data_ex)


def test_triage_07_triage_accept_links_node_with_picker_selection(tmp_path: Path) -> None:
    """TRIAGE-07: Triage accept parses selected target node from picker and creates edge."""
    event_log = FileEventLog(log_path=tmp_path / "events.jsonl")
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log)
    for n in _sample_nodes():
        store.write_node(n, author=n.author)

    inbox_item = store.append_inbox("Need a glare shield test protocol")
    app = create_app(store=store)
    client = TestClient(app)

    form_payload = {
        "item_id": inbox_item.id,
        "node_type": "idea",
        "title": "Sunlight test protocol",
        "body": "Test rig using 1000W halogen lamp to simulate direct midday sun.",
        "domain": "cycling",
        "tags": "testing, optics",
        "keywords": "simulation, glare",
        "edge_target": "FRI-A01 — Bike computer screens washed out in sunlight",
        "edge_rel": "addresses",
        "edge_note": "Validation protocol for friction",
    }
    res = client.post("/triage/accept", data=form_payload, follow_redirects=False)
    assert res.status_code == 303

    nodes = store.list_nodes()
    created = next((n for n in nodes if n.title == "Sunlight test protocol"), None)
    assert created is not None
    assert len(created.edges) == 1
    assert created.edges[0].to_id == "FRI-A01"
    assert created.edges[0].relation == "addresses"
    assert created.edges[0].note == "Validation protocol for friction"


def test_explore_09_node_link_action_with_picker_selection(tmp_path: Path) -> None:
    """EXPLORE-09: Node detail link action accepts picker selection and creates edge."""
    event_log = FileEventLog(log_path=tmp_path / "events.jsonl")
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log)
    for n in _sample_nodes():
        store.write_node(n, author=n.author)

    app = create_app(store=store)
    client = TestClient(app)

    form_payload = {
        "target_id": "OBS-A01 — E-ink price drops on flexible substrates",
        "relation": "informed_by",
        "note": "Using cheap flexible epaper for the puck display",
    }
    res = client.post("/node/IDEA-A01/link", data=form_payload, follow_redirects=False)
    assert res.status_code == 303

    updated = store.get_node("IDEA-A01")
    assert updated is not None
    edge = next((e for e in updated.edges if e.to_id == "OBS-A01"), None)
    assert edge is not None
    assert edge.relation == "informed_by"
    assert edge.note == "Using cheap flexible epaper for the puck display"
