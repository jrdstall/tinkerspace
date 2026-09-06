"""Behaviour tests for zero-classification quick capture and inbox operations.

Traces CAPTURE-01 through CAPTURE-04 per docs/design/specs/CAPTURE.md.
"""

from pathlib import Path
from starlette.testclient import TestClient

from iw.adapters.capture import QuickCaptureInlet
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.web.app import create_app


def test_capture_01_quick_capture_saves_raw_thought_without_classification(tmp_path: Path):
    """CAPTURE-01: Zero-classification capture creates a raw inbox item on disk with no metadata asked."""
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


def test_capture_02_inbox_lists_synced_files_and_quick_lines(tmp_path: Path):
    """CAPTURE-02: Inbox manager discovers both standalone files and quick.txt lines."""
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


def test_capture_03_web_capture_endpoint_creates_inbox_item_and_updates_count(tmp_path: Path):
    """CAPTURE-03: POST /capture appends item to inbox and Explore page reflects updated count."""
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


def test_capture_04_delete_inbox_item_removes_file_from_disk(tmp_path: Path):
    """CAPTURE-04: Deleting an inbox item removes it from disk and list_inbox."""
    store = MarkdownStore(vault_dir=tmp_path)
    item = store.append_inbox("Temporary thought to be discarded")

    assert len(store.list_inbox()) == 1
    deleted = store.delete_inbox_item(item.id)

    assert deleted is True
    assert len(store.list_inbox()) == 0


def test_capture_05_crlf_and_blank_lines_preserved_without_line_multiplication(tmp_path: Path):
    """CAPTURE-05: Multi-line captures with blank lines preserve single blank line without Windows CRLF multiplication."""
    store = MarkdownStore(vault_dir=tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    # 1. Post thought containing single blank line formatted as Windows CRLF (\r\n\r\n)
    client.post(
        "/capture",
        data={"raw_text": "Paragraph one.\r\n\r\nParagraph two with details."},
        follow_redirects=True,
    )

    items = store.list_inbox()
    assert len(items) == 1
    item = items[0]

    # Verify parsed text in store has exact single blank line (2 newlines, not 4)
    assert item.raw_text == "Paragraph one.\n\nParagraph two with details."
    assert item.raw_text.splitlines() == ["Paragraph one.", "", "Paragraph two with details."]

    # Verify file bytes on disk use clean Unix LF without \r\r\n doubling
    inbox_files = list((tmp_path / "inbox").glob("*.md"))
    assert len(inbox_files) == 1
    raw_bytes = inbox_files[0].read_bytes()
    assert b"\r\r\n" not in raw_bytes
    assert b"\r\n" not in raw_bytes

    # Verify triage page renders the textarea with exact single blank line
    res_triage = client.get("/triage")
    assert res_triage.status_code == 200
    assert "Paragraph one.\n\nParagraph two with details." in res_triage.text
    assert "Paragraph one.\n\n\n\nParagraph two" not in res_triage.text

    # Verify historical file with \r\r\n is self-healing on read
    historical_file = tmp_path / "inbox" / "INB-historical-test.md"
    historical_file.write_bytes(b"Old thought header.\r\r\n\r\r\nOld thought body.\n")
    reloaded_items = store.list_inbox()
    hist_item = next(it for it in reloaded_items if it.id == "INB-historical-test")
    assert hist_item.raw_text == "Old thought header.\n\nOld thought body."

