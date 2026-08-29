"""Event log behaviour tests.

Proves the append-only event log records mutations and lifecycle events.
"""

from datetime import datetime, timezone
from pathlib import Path

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore


def test_event_log_appends_immutable_jsonl_records(tmp_path: Path):
    """Event log writes valid JSONL lines and reads them back."""
    log_file = tmp_path / "events.jsonl"
    event_log = FileEventLog(log_path=log_file)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    rec1 = event_log.append(
        kind="test_event_1",
        subject_id="FRI-A01",
        author=author,
        payload={"note": "first"},
    )
    rec2 = event_log.append(
        kind="test_event_2",
        subject_id="FRI-A02",
        author=author,
        payload={"note": "second"},
    )

    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    records = event_log.read_events()
    assert len(records) == 2
    assert records[0].id == rec1.id
    assert records[0].subject_id == "FRI-A01"
    assert records[0].author is not None
    assert records[0].author.kind == AuthorKind.HUMAN
    assert records[1].id == rec2.id
    assert records[1].subject_id == "FRI-A02"


def test_store_write_emits_event_log_record(tmp_path: Path):
    """MarkdownStore writing a node appends an event to the configured EventLog."""
    log_file = tmp_path / "events.jsonl"
    event_log = FileEventLog(log_path=log_file)
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    node = Node(
        id="FRI-A01",
        type="friction",
        title="Event emitter test",
        created=datetime.now(timezone.utc),
        domain="meta",
        tags=["event"],
        body="Prose content",
    )
    store.write_node(node, author=author)

    records = event_log.read_events()
    assert len(records) == 1
    assert records[0].kind == "node_written"
    assert records[0].subject_id == "FRI-A01"
    assert records[0].payload["title"] == "Event emitter test"
