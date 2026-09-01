"""Contract tests for Bookkeeper implementations."""

from pathlib import Path
import pytest

from iw.contracts.bookkeeper import BookkeeperProtocol, StoredArtifact
from iw.adapters.bookkeeper import FileBookkeeper


def test_file_bookkeeper_implements_protocol(tmp_path: Path):
    """Ensure FileBookkeeper conforms to BookkeeperProtocol."""
    bk = FileBookkeeper(tmp_path / "bookkeeper")
    assert isinstance(bk, BookkeeperProtocol)
