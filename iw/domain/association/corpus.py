"""Corpus distillation utilities for association pairing pool.

Layer 2 Domain module. Depends only on iw.contracts and stdlib.
Governed by Vision §13 and SAMPLER-01, SAMPLER-02, SAMPLER-03.
"""

from iw.contracts.association import DistilledRecord
from iw.contracts.models import Node
from iw.contracts.store import StoreProtocol

POOL_NODE_TYPES = {"friction", "observation", "idea", "asset"}


def distill_node(node: Node) -> DistilledRecord:
    """Project full Node into lightweight DistilledRecord without filesystem paths."""
    origin_str = "manual"
    if node.author:
        origin_str = node.author.declared_model or node.author.courier or node.author.kind.value

    clean_body = node.body.strip().replace("\r", " ")
    first_paragraph = clean_body.split("\n\n")[0] if clean_body else node.title
    excerpt = first_paragraph[:200].strip()

    return DistilledRecord(
        id=node.id,
        title=node.title,
        type=node.type,
        domain=node.domain,
        tags=list(node.tags),
        origin=origin_str,
        state=node.state,
        excerpt=excerpt,
    )


def distill_corpus_pool(store: StoreProtocol) -> list[DistilledRecord]:
    """Extract pairing pool of frictions, observations, ideas, and assets state-blindly."""
    all_nodes = store.list_nodes()
    return [
        distill_node(n)
        for n in all_nodes
        if n.type.lower() in POOL_NODE_TYPES
    ]
