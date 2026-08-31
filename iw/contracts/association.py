"""Association Sampler and Distilled Record Contracts.

Layer 1 Contract module. Protocol definitions and types only.
Governed by Vision §13 and SAMPLER specification.
"""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class DistilledRecord:
    """Lightweight projection of a corpus node for pairing and context delivery."""
    id: str
    title: str
    type: str
    domain: str
    tags: list[str] = field(default_factory=list)
    origin: str = "manual"
    state: str = "active"
    excerpt: str = ""


@dataclass(frozen=True)
class PairCandidate:
    """Pair of nodes selected by a sampler strategy for creativity analysis."""
    pair_id: str
    node_a: DistilledRecord
    node_b: DistilledRecord
    strategy: str
    distance_metric: float = 1.0


class AssociationSamplerProtocol(Protocol):
    """Protocol for competing association pairing sampler algorithms."""

    def sample_pairs(
        self,
        pool: list[DistilledRecord],
        count: int = 5,
        seed: int | None = None,
    ) -> list[PairCandidate]:
        """Sample pairing candidates from the distilled corpus pool."""
        ...
