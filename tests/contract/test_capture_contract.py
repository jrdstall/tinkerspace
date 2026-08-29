"""Contract compliance tests for capture inlets.

Proves that QuickCaptureInlet satisfies the CaptureInletProtocol contract.
"""

from pathlib import Path

from iw.adapters.capture import QuickCaptureInlet
from iw.contracts.capture import CaptureInletProtocol
from iw.core.store import MarkdownStore


def test_quick_capture_inlet_satisfies_capture_inlet_protocol(tmp_path: Path):
    """QuickCaptureInlet must implement all methods of CaptureInletProtocol."""
    store = MarkdownStore(vault_dir=tmp_path)
    inlet = QuickCaptureInlet(store=store)
    assert isinstance(inlet, CaptureInletProtocol)
    assert inlet.name == "quick-capture"
