"""Behaviour tests for multi-device store sync and commit-on-refresh.

Traces STORE-10, STORE-12, STORE-13, and STORE-19 per DA-02 §05 and specs/STORE.md.
"""

from pathlib import Path
import shutil
import subprocess
from starlette.testclient import TestClient

from iw.adapters.git import GitCommitter
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.web.app import create_app


def test_sync_arrived_note_is_discovered_without_watchers(tmp_path: Path):
    """STORE-10 & STORE-13: A note arriving via sync is read without background watchers."""
    store = MarkdownStore(vault_dir=tmp_path)

    # Note is created externally in vault by sync or tablet markdown editor
    obs_dir = tmp_path / "observation"
    obs_dir.mkdir(parents=True)
    external_file = obs_dir / "2026-08-29-synced-note.md"
    external_file.write_text(
        "---\n"
        "id: OBS-A01\n"
        "type: observation\n"
        "title: Synced note created on tablet in Obsidian\n"
        "created: 2026-08-29T12:00:00Z\n"
        "domain: hardware\n"
        "tags: [tablet, sync]\n"
        "state: active\n"
        "---\n"
        "Typed while offline on the tablet and synced.\n",
        encoding="utf-8",
    )

    # Discovery happens upon reading/scanning without background watcher
    node = store.get_node("OBS-A01")
    assert node is not None
    assert node.title == "Synced note created on tablet in Obsidian"
    assert "Typed while offline on the tablet and synced." in node.body


def test_commit_what_arrived_on_refresh_creates_git_commit_and_event(tmp_path: Path):
    """STORE-12: External notes arriving via sync are committed to local Git on refresh."""
    git_bin = shutil.which("git")
    if not git_bin:
        return

    # Init test git repository in tmp_path
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test Runner"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@innovators.local"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )

    event_log = FileEventLog(log_path=tmp_path / "events.jsonl")
    git_committer = GitCommitter(vault_dir=tmp_path)
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log, git_committer=git_committer)

    # Initial clean state (commit initial files if any)
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial", "--allow-empty"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )

    # External file arrives via sync
    fri_dir = tmp_path / "friction"
    fri_dir.mkdir(parents=True)
    synced_note = fri_dir / "2026-08-29-tablet-friction.md"
    synced_note.write_text(
        "---\n"
        "id: FRI-A01\n"
        "type: friction\n"
        "title: Friction arrived from tablet sync\n"
        "created: 2026-08-29T14:00:00Z\n"
        "domain: meta\n"
        "tags: [sync]\n"
        "state: active\n"
        "---\n"
        "Note body from tablet\n",
        encoding="utf-8",
    )

    # Call sync_refresh (e.g. triggered when opening web Explore or on refresh)
    synced_ids = store.sync_refresh()
    assert "FRI-A01" in synced_ids

    # Verify local Git commit was created with external sync author
    log_res = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%an|%s"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    assert "External Sync" in log_res.stdout
    assert "sync:" in log_res.stdout

    # Verify event log received node_synced record
    events = event_log.read_events()
    assert any(e.kind == "node_synced" and e.subject_id == "FRI-A01" for e in events)


def test_sync_conflict_file_is_quarantined_in_needs_attention(tmp_path: Path):
    """STORE-19: Sync conflict duplicate files (.sync-conflict-*) are quarantined."""
    store = MarkdownStore(vault_dir=tmp_path)
    idea_dir = tmp_path / "idea"
    idea_dir.mkdir(parents=True)

    conflict_file = idea_dir / "2026-08-29-bike.sync-conflict-20260829-140000-TABLET.md"
    conflict_file.write_text(
        "---\n"
        "id: IDEA-A01\n"
        "type: idea\n"
        "title: Conflicting bike idea\n"
        "---\n"
        "Conflict body\n",
        encoding="utf-8",
    )

    attention_items = store.list_needs_attention()
    assert len(attention_items) == 1
    assert "sync-conflict" in attention_items[0].filepath
    assert "Sync conflict file" in attention_items[0].reason


def test_explore_page_displays_attention_banner_on_sync_conflict(tmp_path: Path):
    """Explore landing page renders the Needs Attention banner when conflict exists."""
    store = MarkdownStore(vault_dir=tmp_path)
    idea_dir = tmp_path / "idea"
    idea_dir.mkdir(parents=True)
    conflict_file = idea_dir / "note.sync-conflict-123.md"
    conflict_file.write_text("broken conflict content\n", encoding="utf-8")

    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200
    assert "Needs Attention" in response.text
    assert "note.sync-conflict-123.md" in response.text
    assert "Sync conflict file" in response.text
