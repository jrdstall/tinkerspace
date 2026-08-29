"""Contract compliance tests for FileDropInlet.

Proves that FileDropInlet satisfies the CaptureInletProtocol contract.
"""

from pathlib import Path
from iw.adapters.capture import FileDropInlet
from iw.contracts.capture import CaptureInletProtocol
from iw.core.store import MarkdownStore


def test_file_drop_inlet_satisfies_capture_inlet_protocol(tmp_path: Path):
    """FileDropInlet must implement all methods of CaptureInletProtocol."""
    store = MarkdownStore(vault_dir=tmp_path)
    inlet = FileDropInlet(store=store)
    assert isinstance(inlet, CaptureInletProtocol)
    assert inlet.name == "file-drop"
