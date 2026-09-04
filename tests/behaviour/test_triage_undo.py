"""Behaviour tests for returning a node to triage inbox.

Traces TRIAGE-05 per docs/design/specs/TRIAGE.md.
"""

from datetime import datetime, timezone
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.core.triage import TriageService
from iw.web.app import create_app


def test_triage_05_return_node_to_inbox_restores_text_and_deletes_node(tmp_path: Path):
    """TRIAGE-05: return_to_inbox deletes node file and appends its body back into inbox."""
    event_log = FileEventLog(log_path=tmp_path / "events.jsonl")
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log)
    service = TriageService(store=store)
    author = Author(kind=AuthorKind.HUMAN, courier="test")

    node = Node(
        id="FRI-A01",
        type="friction",
        title="Accidentally submitted thought",
        created=datetime.now(timezone.utc),
        domain="kitchen",
        tags=["cooking"],
        state="active",
        body="Make a cheap wall-mountable screen for recipes",
    )
    store.write_node(node, author=author)
    assert store.get_node("FRI-A01") is not None
    assert len(service.list_inbox_items()) == 0

    item = service.return_to_inbox("FRI-A01", author=author)

    assert item is not None
    assert item.raw_text == "Make a cheap wall-mountable screen for recipes"
    assert store.get_node("FRI-A01") is None
    assert len(service.list_inbox_items()) == 1


def test_triage_05_web_return_to_triage_endpoint_and_banner(tmp_path: Path):
    """TRIAGE-05: POST /node/{node_id}/return_to_triage redirects to /triage and restores item."""
    store = MarkdownStore(vault_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)
    author = Author(kind=AuthorKind.HUMAN, courier="test")

    node = Node(
        id="IDEA-A01",
        type="idea",
        title="Voice assistant timer",
        created=datetime.now(timezone.utc),
        domain="home",
        tags=["iot"],
        state="active",
        body="Timer with tactile physical dial.",
    )
    store.write_node(node, author=author)

    # Trigger return to triage
    res = client.post("/node/IDEA-A01/return_to_triage", follow_redirects=True)
    assert res.status_code == 200
    assert store.get_node("IDEA-A01") is None

    # Triage view should now have that item
    assert "Timer with tactile physical dial." in res.text

    # Verify banner renders with query parameters
    res_banner = client.get("/triage?created=FRI-A02&type=friction")
    assert res_banner.status_code == 200
    assert "✓ Triaged FRI-A02" in res_banner.text
    assert "↩️ Undo / Re-triage FRI-A02" in res_banner.text
