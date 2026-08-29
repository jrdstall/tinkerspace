"""Behaviour tests for local Git auto-commit on store write operations.

Traces STORE-12 per specs/STORE.md.
"""

from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

from iw.adapters.git import GitCommitter
from iw.contracts.models import Author, AuthorKind, Node
from iw.core.store import MarkdownStore


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
