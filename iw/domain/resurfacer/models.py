"""Data models for Resurfacer Engine and Observation Sweeps.

Layer 2 Domain module. Depends on iw.contracts and stdlib.
Governed by Vision §13 and RESURF-01 through RESURF-06.
"""

from dataclasses import dataclass, field
from iw.contracts.models import Node


@dataclass(frozen=True)
class ResurfacedNode:
    """A dormant corpus node identified for resurfacing."""
    node: Node
    dormancy_score: float
    days_since_touched: int
    edge_count: int
    reason: str


@dataclass(frozen=True)
class SweepCluster:
    """Cluster of related observations identified during sweep."""
    theme: str
    observation_ids: list[str] = field(default_factory=list)
    synthesis_notes: str = ""
    suggested_subject_id: str | None = None
