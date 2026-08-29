"""Contract compliance test suite.

Proves that concrete implementations satisfy the Protocol contracts in iw.contracts.
"""

from pathlib import Path
from iw.contracts.event_log import EventLogProtocol
from iw.contracts.store import StoreProtocol
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore


def test_markdown_store_satisfies_store_protocol(tmp_path: Path):
    """MarkdownStore must implement all methods of StoreProtocol."""
    store = MarkdownStore(vault_dir=tmp_path)
    assert isinstance(store, StoreProtocol)


def test_file_event_log_satisfies_event_log_protocol(tmp_path: Path):
    """FileEventLog must implement all methods of EventLogProtocol."""
    log_path = tmp_path / "events.jsonl"
    event_log = FileEventLog(log_path=log_path)
    assert isinstance(event_log, EventLogProtocol)
