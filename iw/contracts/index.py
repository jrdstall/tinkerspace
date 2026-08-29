"""Index query and search protocol."""

from typing import Protocol, runtime_checkable
from iw.contracts.models import Node, NodeSummary, QueryFilters


@runtime_checkable
class IndexProtocol(Protocol):
    """Layer 1 index query protocol for searching and filtering the corpus."""

    def query(self, filters: QueryFilters) -> list[NodeSummary]:
        """Return node summaries matching structured filter criteria."""
        ...

    def search(self, text: str) -> list[NodeSummary]:
        """Perform full-text search across node titles, tags, and bodies."""
        ...

    def rebuild(self, nodes: list[Node]) -> None:
        """Deterministically rebuild index state from raw nodes."""
        ...
