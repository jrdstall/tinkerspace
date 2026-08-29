"""Contract compliance tests for TriageProtocol.

Proves that TriageService satisfies the TriageProtocol contract.
"""

from pathlib import Path

from iw.contracts.triage import TriageProtocol
from iw.core.store import MarkdownStore
from iw.core.triage import TriageService


def test_triage_service_satisfies_triage_protocol(tmp_path: Path):
    """TriageService must implement all methods of TriageProtocol."""
    store = MarkdownStore(vault_dir=tmp_path)
    service = TriageService(store=store)
    assert isinstance(service, TriageProtocol)
