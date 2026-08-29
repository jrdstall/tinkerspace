"""STORE subsystem behaviour tests for friction nodes.

Traces and proves STORE-01 through STORE-16 per docs/design/specs/STORE.md.
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.store import MarkdownStore


def test_store_01_node_reads_frontmatter_and_prose_from_markdown_file(tmp_path: Path):
    """STORE-01: A node is one markdown file with YAML frontmatter and prose body."""
    friction_dir = tmp_path / "friction"
    friction_dir.mkdir(parents=True)
    file_path = friction_dir / "2026-08-29-noisy-chain.md"
    file_path.write_text(
        "---\n"
        "id: FRI-A01\n"
        "type: friction\n"
        "title: Chain makes grinding sound under load\n"
        "created: 2026-08-29T10:00:00Z\n"
        "domain: cycling\n"
        "tags: [drivetrain, maintenance]\n"
        "state: active\n"
        "---\n"
        "Whenever shifting into the smallest cog, the chain rubs against the cage.\n",
        encoding="utf-8",
    )

    store = MarkdownStore(vault_dir=tmp_path)
    node = store.get_node("FRI-A01")

    assert node is not None
    assert node.id == "FRI-A01"
    assert node.type == "friction"
    assert node.title == "Chain makes grinding sound under load"
    assert node.domain == "cycling"
    assert node.tags == ["drivetrain", "maintenance"]
    assert node.state == "active"
    assert "Whenever shifting into the smallest cog" in node.body


def test_store_02_reads_always_hit_disk_without_caching(tmp_path: Path):
    """STORE-02: Reading a node never caches; external edits are seen immediately."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    node = Node(
        id="FRI-A02",
        type="friction",
        title="Original title",
        created=datetime.now(timezone.utc),
        domain="cycling",
        tags=["gear"],
    )
    store.write_node(node, author=author)

    assert store.get_node("FRI-A02").title == "Original title"

    # Simulate an external writer (Obsidian or sync) updating the title directly on disk
    target_file = next(tmp_path.rglob("*.md"))
    content = target_file.read_text(encoding="utf-8")
    updated_content = content.replace("Original title", "Externally modified title")
    target_file.write_text(updated_content, encoding="utf-8")

    # Second read must reflect disk modification immediately without caching
    fresh_node = store.get_node("FRI-A02")
    assert fresh_node is not None
    assert fresh_node.title == "Externally modified title"


def test_store_03_04_writing_preserves_untouched_frontmatter_and_existing_body(tmp_path: Path):
    """STORE-03 & STORE-04: Writing modifies only supplied keys, preserving extra frontmatter and prose."""
    friction_dir = tmp_path / "friction"
    friction_dir.mkdir(parents=True)
    file_path = friction_dir / "2026-08-29-stem.md"
    file_path.write_text(
        "---\n"
        "id: FRI-A03\n"
        "type: friction\n"
        "title: Old Title\n"
        "created: 2026-08-29T10:00:00Z\n"
        "domain: cycling\n"
        "tags: [hardware]\n"
        "custom_preserved_key: do_not_delete_this\n"
        "stem: There has to be a better way\n"
        "---\n"
        "Original body text that must be preserved.\n",
        encoding="utf-8",
    )

    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.AGENT, courier="mcp-pull")
    node = store.get_node("FRI-A03")
    assert node is not None

    node.title = "New Updated Title"
    node.body = ""  # Empty body in update object means preserve existing body
    store.write_node(node, author=author)

    raw_text = file_path.read_text(encoding="utf-8")
    assert "New Updated Title" in raw_text
    assert "custom_preserved_key: do_not_delete_this" in raw_text
    assert "stem: There has to be a better way" in raw_text
    assert "Original body text that must be preserved." in raw_text


def test_store_05_writes_are_atomic_leaving_no_leftover_temp_files(tmp_path: Path):
    """STORE-05: Writes are atomic via temporary files and rename."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    node = Node(
        id="FRI-A05",
        type="friction",
        title="Atomic write test",
        created=datetime.now(timezone.utc),
        domain="testing",
        tags=["atomic"],
        body="Testing atomic write file persistence.",
    )
    written = store.write_node(node, author=author)

    assert written.id == "FRI-A05"
    temp_files = list(tmp_path.rglob(".*.tmp"))
    assert len(temp_files) == 0


def test_store_06_unparseable_yaml_quarantined_in_needs_attention(tmp_path: Path):
    """STORE-06: A file whose YAML frontmatter fails to parse is quarantined."""
    bad_dir = tmp_path / "friction"
    bad_dir.mkdir(parents=True)
    bad_file = bad_dir / "broken.md"
    bad_file.write_text(
        "---\n"
        "id: FRI-BROKEN\n"
        "title: [unterminated list\n"
        "---\n"
        "Body content\n",
        encoding="utf-8",
    )

    store = MarkdownStore(vault_dir=tmp_path)
    attention = store.list_needs_attention()

    assert len(attention) == 1
    assert "broken.md" in attention[0].filepath
    assert "YAML parse error" in attention[0].reason
    assert store.get_node("FRI-BROKEN") is None


def test_store_07_missing_id_quarantined_in_needs_attention(tmp_path: Path):
    """STORE-07: A file without an ID is quarantined in needs-attention list."""
    friction_dir = tmp_path / "friction"
    friction_dir.mkdir(parents=True)
    file_path = friction_dir / "noid.md"
    file_path.write_text(
        "---\n"
        "type: friction\n"
        "title: Note without ID\n"
        "---\n"
        "Prose body\n",
        encoding="utf-8",
    )

    store = MarkdownStore(vault_dir=tmp_path)
    attention = store.list_needs_attention()

    assert len(attention) == 1
    assert "noid.md" in attention[0].filepath
    assert "Missing or invalid id" in attention[0].reason


def test_store_08_resolving_id_scans_frontmatter_regardless_of_filename(tmp_path: Path):
    """STORE-08: Resolving entity ID scans frontmatter without relying on filename pattern."""
    misc_dir = tmp_path / "arbitrary_folder"
    misc_dir.mkdir(parents=True)
    odd_file = misc_dir / "random_notes_export_99.md"
    odd_file.write_text(
        "---\n"
        "id: FRI-A08\n"
        "type: friction\n"
        "title: Scanned anywhere\n"
        "created: 2026-08-29T10:00:00Z\n"
        "domain: meta\n"
        "tags: [scan]\n"
        "---\n"
        "Found regardless of path or filename.\n",
        encoding="utf-8",
    )

    store = MarkdownStore(vault_dir=tmp_path)
    node = store.get_node("FRI-A08")

    assert node is not None
    assert node.title == "Scanned anywhere"


def test_store_11_write_requires_explicit_author_attribution(tmp_path: Path):
    """STORE-11: Every write initiated by the service requires an explicit author."""
    store = MarkdownStore(vault_dir=tmp_path)
    node = Node(
        id="FRI-A11",
        type="friction",
        title="Author required test",
        created=datetime.now(timezone.utc),
        domain="meta",
        tags=["attribution"],
    )

    with pytest.raises(ValueError, match="Author with kind is required"):
        store.write_node(node, author=None)  # type: ignore


def test_store_16_id_lookup_is_case_insensitive(tmp_path: Path):
    """STORE-16: ID lookups are case-insensitive on input."""
    friction_dir = tmp_path / "friction"
    friction_dir.mkdir(parents=True)
    file_path = friction_dir / "2026-08-29-case.md"
    file_path.write_text(
        "---\n"
        "id: FRI-A16\n"
        "type: friction\n"
        "title: Case insensitive lookup\n"
        "created: 2026-08-29T10:00:00Z\n"
        "domain: meta\n"
        "tags: [case]\n"
        "---\n"
        "Body content\n",
        encoding="utf-8",
    )

    store = MarkdownStore(vault_dir=tmp_path)
    node_lower = store.get_node("fri-a16")
    node_upper = store.get_node("FRI-A16")

    assert node_lower is not None
    assert node_upper is not None
    assert node_lower.id == "FRI-A16"
    assert node_upper.id == "FRI-A16"
