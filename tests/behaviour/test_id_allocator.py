"""Behaviour tests for deterministic ID allocation.

Traces STORE-14, STORE-15, and STORE-16 per DA-01 and STORE.md.
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.ids import (
    allocate_next_id,
    index_to_sequence,
    sequence_to_index,
)
from iw.core.store import MarkdownStore


def test_id_sequence_indexing_single_letter():
    """Sequence index accurately maps A01 through Z99 excluding I and O."""
    assert sequence_to_index("A01") == 0
    assert sequence_to_index("A99") == 98
    assert sequence_to_index("B01") == 99

    # H is letter index 7 (7 * 99 + 98 = 791)
    assert sequence_to_index("H99") == 791
    # J is letter index 8 (skipping I: 8 * 99 + 0 = 792)
    assert sequence_to_index("J01") == 792

    # N is letter index 12 (12 * 99 + 98 = 1286)
    assert sequence_to_index("N99") == 1286
    # P is letter index 13 (skipping O: 13 * 99 + 0 = 1287)
    assert sequence_to_index("P01") == 1287

    # Z is letter index 23 (23 * 99 + 98 = 2375)
    assert sequence_to_index("Z99") == 2375


def test_id_sequence_indexing_two_letter_overflow():
    """Sequence index maps AA01 through ZZ99 correctly."""
    assert sequence_to_index("AA01") == 2376
    assert sequence_to_index("AA99") == 2474
    assert sequence_to_index("AB01") == 2475


def test_id_index_to_sequence_roundtrip():
    """Indices map back to exact sequence strings."""
    assert index_to_sequence(0) == "A01"
    assert index_to_sequence(98) == "A99"
    assert index_to_sequence(99) == "B01"
    assert index_to_sequence(791) == "H99"
    assert index_to_sequence(792) == "J01"
    assert index_to_sequence(2375) == "Z99"
    assert index_to_sequence(2376) == "AA01"


def test_id_sequence_rejects_forbidden_letters_i_and_o():
    """Characters I and O are forbidden in letter positions."""
    with pytest.raises(ValueError):
        sequence_to_index("I01")
    with pytest.raises(ValueError):
        sequence_to_index("O01")
    with pytest.raises(ValueError):
        sequence_to_index("AI01")


def test_allocate_next_id_empty_and_sequential():
    """Empty vault allocates A01; existing items allocate next sequential ID."""
    assert allocate_next_id("FRI", []) == "FRI-A01"
    assert allocate_next_id("idea", ["IDEA-A01", "IDEA-A02"]) == "IDEA-A03"
    assert allocate_next_id("QUE", ["que-a01", "que-a09"]) == "QUE-A10"
    assert allocate_next_id("EXP", ["EXP-H99"]) == "EXP-J01"


def test_store_allocate_id_respects_existing_nodes_and_deleted_event_logs(tmp_path: Path):
    """STORE-14 & STORE-15: Store allocates next ID and never reuses deleted IDs."""
    event_log = FileEventLog(log_path=tmp_path / "events.jsonl")
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    # Initial allocation
    id1 = store.allocate_id("IDEA")
    assert id1 == "IDEA-A01"

    # Write node
    node1 = Node(
        id=id1,
        type="idea",
        title="First idea",
        created=datetime.now(timezone.utc),
        domain="cycling",
        tags=["display"],
    )
    store.write_node(node1, author=author)

    # Next allocation is IDEA-A02
    id2 = store.allocate_id("IDEA")
    assert id2 == "IDEA-A02"

    # Write second node
    node2 = Node(
        id=id2,
        type="idea",
        title="Second idea",
        created=datetime.now(timezone.utc),
        domain="cycling",
        tags=["display"],
    )
    store.write_node(node2, author=author)

    # Simulate deleting the second node's file on disk
    idea_files = list(tmp_path.rglob("*.md"))
    for f in idea_files:
        if "second-idea" in f.name:
            f.unlink()

    # Next allocation must STILL be IDEA-A03 (never reusing IDEA-A02 because of event log)
    id3 = store.allocate_id("IDEA")
    assert id3 == "IDEA-A03"
