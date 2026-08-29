"""Capture inlet protocol definition."""

from typing import Protocol, runtime_checkable
from iw.contracts.models import InboxItem


@runtime_checkable
class CaptureInletProtocol(Protocol):
    """Layer 3 capture inlet adapter for receiving raw inputs into the inbox."""

    @property
    def name(self) -> str:
        """Name of the inlet (e.g. 'quick-capture', 'file-drop', 'sync-inbox')."""
        ...

    def capture(self, raw_text: str, source_file: str | None = None) -> InboxItem:
        """Append raw captured thought to the store inbox."""
        ...
