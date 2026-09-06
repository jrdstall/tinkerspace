"""Behaviour tests for local Git auto-commit on store write operations.

Traces STORE-12 per specs/STORE.md.
"""

from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

from iw.adapters.git import GitCommitter
from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.core.triage import TriageService


def test_git_commit_is_created_on_node_write_when_repo_exists(tmp_path: Path):
    """STORE-12: Every successful write operation creates a local Git commit in the vault."""
    git_bin = shutil.which("git")
    if not git_bin:
        # Skip if git is not in PATH
        return

    # Initialize a test git repository in tmp_path
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

    git_committer = GitCommitter(vault_dir=tmp_path)
    store = MarkdownStore(vault_dir=tmp_path, git_committer=git_committer)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    node = Node(
        id="IDEA-A01",
        type="idea",
        title="Handlebar concept with git commit",
        created=datetime.now(timezone.utc),
        domain="cycling",
        tags=["hardware"],
        body="Prose content",
    )
    store.write_node(node, author=author)

    # Check git log output
    log_res = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%an|%s"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Jared" in log_res.stdout
    assert "IDEA-A01" in log_res.stdout
    assert "Handlebar concept with git commit" in log_res.stdout


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=str(path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=str(path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@innovators.local"], cwd=str(path), check=True, capture_output=True)


def test_events_jsonl_is_staged_and_committed_with_node_write(tmp_path: Path):
    """STORE-12, EVENT-01: Writing a node commits both the node markdown file and events.jsonl."""
    if not shutil.which("git"):
        return

    _init_git_repo(tmp_path)
    event_log = FileEventLog(log_path=tmp_path / "events.jsonl")
    git_committer = GitCommitter(vault_dir=tmp_path)
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log, git_committer=git_committer)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    node = Node(
        id="IDEA-A02",
        type="idea",
        title="Audit trail git commit",
        created=datetime.now(timezone.utc),
        domain="software",
        tags=["git"],
        body="Prose content",
    )
    store.write_node(node, author=author)

    # Git status should be completely clean
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    assert status.stdout.strip() == ""

    # Commit should have touched both the node and events.jsonl
    show = subprocess.run(
        ["git", "show", "--name-only", "--pretty=format:"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    files = [f.strip() for f in show.stdout.splitlines() if f.strip()]
    assert "events.jsonl" in files
    assert any(f.endswith(".md") for f in files)


def test_inbox_capture_and_discard_commits_and_leaves_clean_status(tmp_path: Path):
    """STORE-12, CAPTURE-04: Capturing and discarding inbox items creates commits and leaves working tree clean."""
    if not shutil.which("git"):
        return

    _init_git_repo(tmp_path)
    event_log = FileEventLog(log_path=tmp_path / "events.jsonl")
    git_committer = GitCommitter(vault_dir=tmp_path)
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log, git_committer=git_committer)

    # 1. Capture thought
    item = store.append_inbox("A fleeting thought to test git", inlet="web-capture")

    # Working tree should be clean after capture
    status1 = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    assert status1.stdout.strip() == ""

    # Verify commit log
    log1 = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%s"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    assert f"capture {item.id}" in log1.stdout

    # 2. Discard thought
    discarded = store.delete_inbox_item(item.id)
    assert discarded is True

    # Working tree should be completely clean — no uncommitted deleted inbox file!
    status2 = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    assert status2.stdout.strip() == ""

    # Verify commit log
    log2 = subprocess.run(
        ["git", "log", "-1", "--pretty=format:%s"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    assert f"discard {item.id}" in log2.stdout


def test_inbox_triage_converts_and_cleans_deleted_inbox_file(tmp_path: Path):
    """STORE-12, TRIAGE-01: Triaging an inbox item creates commits for the new node and inbox cleanup."""
    if not shutil.which("git"):
        return

    _init_git_repo(tmp_path)
    event_log = FileEventLog(log_path=tmp_path / "events.jsonl")
    git_committer = GitCommitter(vault_dir=tmp_path)
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log, git_committer=git_committer)
    author = Author(kind=AuthorKind.HUMAN, courier="triage-ui")

    item = store.append_inbox("Thought ready for triage", inlet="web-capture")
    assert len(store.list_inbox()) == 1

    triage_service = TriageService(store=store)
    node_to_create = Node(
        id="",
        type="idea",
        title="Triaged Concept",
        created=datetime.now(timezone.utc),
        domain="engineering",
        tags=["concept"],
        body="Converted from inbox item",
    )
    saved_node = triage_service.triage_item(item_id=item.id, node=node_to_create, author=author)
    assert saved_node.id != ""
    assert len(store.list_inbox()) == 0

    # Working tree should be completely clean
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    assert status.stdout.strip() == ""
