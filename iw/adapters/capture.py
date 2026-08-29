"""Capture inlet adapters for receiving raw thoughts and file drops.

Layer 3 Adapters implementing CaptureInletProtocol.
"""

from iw.contracts.capture import CaptureInletProtocol
from iw.contracts.models import InboxItem
from iw.contracts.store import StoreProtocol


class QuickCaptureInlet(CaptureInletProtocol):
    """Inlet for desktop hotkey and form quick capture."""

    def __init__(self, store: StoreProtocol) -> None:
        self.store = store

    @property
    def name(self) -> str:
        """Name of the inlet."""
        return "quick-capture"

    def capture(self, raw_text: str, source_file: str | None = None) -> InboxItem:
        """Append raw captured thought to the store inbox without classification."""
        return self.store.append_inbox(
            raw_text=raw_text,
            inlet=self.name,
            source_filename=source_file,
        )


class FileDropInlet(CaptureInletProtocol):
    """Inlet for dropped sketches, media, and reference documents."""

    def __init__(self, store: StoreProtocol) -> None:
        self.store = store

    @property
    def name(self) -> str:
        """Name of the inlet."""
        return "file-drop"

    def capture(self, raw_text: str, source_file: str | None = None) -> InboxItem:
        """Capture dropped file notice into inbox."""
        return self.store.append_inbox(
            raw_text=raw_text,
            inlet=self.name,
            source_filename=source_file,
        )
