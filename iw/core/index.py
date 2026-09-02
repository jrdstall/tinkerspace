"""Layer 1 Core InMemory Index and Search implementation.

Provides fast multi-facet filtering and full-text search across all nodes.
"""

from typing import Any
from iw.contracts.index import IndexProtocol
from iw.contracts.models import Node, NodeSummary, QueryFilters


class InMemoryIndex(IndexProtocol):
    """Ephemeral in-memory index for querying and searching node collections."""

    def __init__(self, nodes: list[Node] | None = None) -> None:
        self._nodes: list[Node] = list(nodes) if nodes else []

    def rebuild(self, nodes: list[Node]) -> None:
        """Deterministically rebuild index state from raw nodes."""
        self._nodes = list(nodes)

    def query(self, filters: QueryFilters) -> list[NodeSummary]:
        """Return node summaries matching structured filter criteria."""
        filtered = self.filter_nodes(self._nodes, filters)
        return [self._to_summary(n) for n in filtered]

    def search(self, text: str) -> list[NodeSummary]:
        """Perform full-text search across node titles, tags, and bodies."""
        q = text.strip().lower()
        corpus = [n for n in self._nodes if not (n.attrs.get("is_subquestion") is True or (n.type == "question" and bool(n.attrs.get("subject_id"))))]
        if not q:
            return [self._to_summary(n) for n in corpus]

        results = [n for n in corpus if self._matches_text(n, q)]
        return [self._to_summary(n) for n in results]

    def filter_and_search(
        self,
        filters: QueryFilters,
        query_text: str | None = None,
        sort_by: str = "touched",
    ) -> list[Node]:
        """Filter, search, and sort full Node objects."""
        nodes = self.filter_nodes(self._nodes, filters)
        if query_text and query_text.strip():
            q = query_text.strip().lower()
            nodes = [n for n in nodes if self._matches_text(n, q)]

        return self.sort_nodes(nodes, sort_by)

    def filter_nodes(self, nodes: list[Node], filters: QueryFilters) -> list[Node]:
        """Apply structured filters to a node list."""
        out: list[Node] = []
        for n in nodes:
            if not filters.include_subquestions:
                if n.attrs.get("is_subquestion") is True or (n.type == "question" and bool(n.attrs.get("subject_id"))):
                    continue
            if filters.type and n.type.lower() != filters.type.lower():
                continue
            if filters.domain and n.domain.lower() != filters.domain.lower():
                continue
            if filters.tag and filters.tag.lower() not in [t.lower() for t in n.tags]:
                continue
            if filters.state and n.state.lower() != filters.state.lower():
                continue
            if filters.min_cml is not None:
                cml_val = int(n.attrs.get("cml", 1))
                if cml_val < filters.min_cml:
                    continue
            out.append(n)
        return out

    def sort_nodes(self, nodes: list[Node], sort_by: str) -> list[Node]:
        """Sort nodes by specified criterion."""
        if sort_by == "created":
            return sorted(nodes, key=lambda n: n.created or 0, reverse=True)
        if sort_by == "id":
            return sorted(nodes, key=lambda n: n.id)
        if sort_by == "title":
            return sorted(nodes, key=lambda n: n.title.lower())
        # Default: last_touched (or created) descending
        return sorted(
            nodes,
            key=lambda n: (n.last_touched or n.created or 0),
            reverse=True,
        )

    def _matches_text(self, node: Node, q: str) -> bool:
        """Check if query text appears in node ID, title, body, domain, or tags."""
        if q in node.id.lower() or q in node.title.lower() or q in node.domain.lower():
            return True
        if q in node.body.lower():
            return True
        return any(q in t.lower() for t in node.tags)

    def _to_summary(self, node: Node) -> NodeSummary:
        """Project full Node into lightweight NodeSummary."""
        cml_val = int(node.attrs.get("cml", 1))
        scores_raw = node.attrs.get("scores", {})
        scores_val: dict[str, int] = {}
        if isinstance(scores_raw, dict):
            for k, v in scores_raw.items():
                if isinstance(v, (int, float)):
                    scores_val[k] = int(v)
        return NodeSummary(
            id=node.id,
            type=node.type,
            title=node.title,
            domain=node.domain,
            tags=node.tags,
            state=node.state,
            cml=cml_val,
            last_touched=node.last_touched,
            scores=scores_val,
            worth_to_me=node.attrs.get("worth_to_me"),
            worth_to_others=node.attrs.get("worth_to_others"),
            concept_graphic=node.attrs.get("concept_graphic"),
        )
