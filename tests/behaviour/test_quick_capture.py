"""Behaviour tests for zero-classification quick capture and inbox operations.

Traces V§14.10 and DA-05 capture routes and inbox formats.
"""

from pathlib import Path
from starlette.testclient import TestClient

from iw.adapters.capture import QuickCaptureInlet
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.web.app import create_app


def test_quick_capture_saves_raw_thought_without_classification(tmp_path: Path):
    """Zero-classification capture creates a raw inbox item on disk with no metadata asked."""
    event_log = FileEventLog(log_path=tmp_path / "events.jsonl")
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log)
    inlet = QuickCaptureInlet(store=store)

    item = inlet.capture("Bike computer batteries die in 5 hours with backlight on")

    assert item is not None
    assert "Bike computer batteries die in 5 hours" in item.raw_text
    assert item.inlet == "quick-capture"

    # Verify file was written into inbox/
    inbox_files = list((tmp_path / "inbox").glob("*.md"))
    assert len(inbox_files) == 1
    assert "Bike computer batteries die" in inbox_files[0].read_text(encoding="utf-8")

    # Verify event log received inbox_captured record
    events = event_log.read_events()
    assert any(e.kind == "inbox_captured" and e.subject_id == item.id for e in events)


def test_inbox_lists_synced_files_and_quick_lines(tmp_path: Path):
    """Inbox manager discovers both standalone files and quick.txt lines."""
    store = MarkdownStore(vault_dir=tmp_path)
    inbox_dir = tmp_path / "inbox"
    inbox_dir.mkdir(parents=True)

    # 1. Add standalone file
    (inbox_dir / "tablet_capture_01.md").write_text("Saddle feels too wide at the rear.\n", encoding="utf-8")

    # 2. Add quick.txt lines
    (inbox_dir / "quick.txt").write_text(
        "Need better hex key set for trail kit\n"
        "Tubeless valve core clogged with dried sealant\n",
        encoding="utf-8",
    )

    items = store.list_inbox()
    assert len(items) == 3

    texts = [i.raw_text for i in items]
    assert "Saddle feels too wide at the rear." in texts
    assert "Need better hex key set for trail kit" in texts
    assert "Tubeless valve core clogged with dried sealant" in texts


def test_web_capture_endpoint_creates_inbox_item_and_updates_count(tmp_path: Path):
    """POST /capture appends item to inbox and Explore page reflects updated count."""
    store = MarkdownStore(vault_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    # 1. Initial explore view has 0 triage items
    res0 = client.get("/")
    assert res0.status_code == 200
    assert 'id="triage-badge">0</span>' in res0.text

    # 2. Post a quick capture
    post_res = client.post(
        "/capture",
        data={"raw_text": "There has to be a better way to clean bike chains quickly"},
        follow_redirects=True,
    )
    assert post_res.status_code == 200
    assert 'id="triage-badge">1</span>' in post_res.text

    # 3. Verify item in store
    items = store.list_inbox()
    assert len(items) == 1
    assert "clean bike chains quickly" in items[0].raw_text


def test_delete_inbox_item_removes_file_from_disk(tmp_path: Path):
    """Deleting an inbox item removes it from disk and list_inbox."""
    store = MarkdownStore(vault_dir=tmp_path)
    item = store.append_inbox("Temporary thought to be discarded")

    assert len(store.list_inbox()) == 1
    deleted = store.delete_inbox_item(item.id)

    assert deleted is True
    assert len(store.list_inbox()) == 0
