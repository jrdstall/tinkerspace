"""Contract compliance tests for IndexProtocol.

Proves that InMemoryIndex satisfies the IndexProtocol contract.
"""

from iw.contracts.index import IndexProtocol
from iw.core.index import InMemoryIndex


def test_in_memory_index_satisfies_index_protocol():
    """InMemoryIndex must implement all methods of IndexProtocol."""
    index = InMemoryIndex()
    assert isinstance(index, IndexProtocol)
