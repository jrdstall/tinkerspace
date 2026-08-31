"""Resurfacer Engine scoring dormancy and observation sweeps.

Layer 2 Domain module. Depends on iw.contracts, iw.domain.resurfacer.models, and stdlib.
Governed by Vision §13 and RESURF-01 through RESURF-06.
"""

from collections import Counter
from datetime import datetime, timezone
from iw.contracts.models import Author, AuthorKind, Node
from iw.contracts.store import StoreProtocol
from iw.domain.resurfacer.models import ResurfacedNode, SweepCluster


def calculate_dormancy_score(
    node: Node,
    now: datetime,
    domain_counts: dict[str, int],
) -> tuple[float, int, str]:
    """Calculate dormancy score (0.0 to 1.0), days elapsed, and primary resurfacing rationale."""
    days = max(0, (now - node.last_touched).days)
    recency_score = min(1.0, days / 30.0) * 0.4

    edge_count = len(node.edges)
    isolation_score = 0.4 if edge_count == 0 else (0.2 if edge_count == 1 else 0.0)

    is_rare = domain_counts.get(node.domain.lower(), 0) <= 2
    domain_score = 0.2 if is_rare else 0.0

    total = round(min(1.0, recency_score + isolation_score + domain_score), 2)
    reasons = []
    if isolation_score >= 0.4:
        reasons.append("Unlinked island")
    if days >= 14:
        reasons.append(f"{days}d dormant")
    if is_rare:
        reasons.append(f"Rare domain ({node.domain})")
    reason_str = " · ".join(reasons) or "Corpus review"

    return total, days, reason_str


class ResurfacerEngine:
    """Calculates dormancy ranking and triggers observation sweep workflows."""

    def __init__(self, store: StoreProtocol) -> None:
        self.store = store

    def find_dormant_nodes(
        self,
        count: int = 5,
        types: set[str] | None = None,
    ) -> list[ResurfacedNode]:
        """Rank and return top dormant corpus nodes."""
        all_nodes = self.store.list_nodes()
        target_types = types or {"friction", "idea", "observation", "asset"}
        pool = [n for n in all_nodes if n.type.lower() in target_types]
        if not pool:
            return []

        counts = Counter(n.domain.lower() for n in all_nodes if n.domain)
        now = datetime.now(timezone.utc)

        scored: list[ResurfacedNode] = []
        for n in pool:
            score, days, reason = calculate_dormancy_score(n, now, counts)
            scored.append(
                ResurfacedNode(
                    node=n,
                    dormancy_score=score,
                    days_since_touched=days,
                    edge_count=len(n.edges),
                    reason=reason,
                )
            )

        scored.sort(key=lambda r: (r.dormancy_score, r.days_since_touched), reverse=True)
        return scored[:count]

    def cluster_observations(self, domain: str | None = None) -> list[SweepCluster]:
        """Aggregate observations by domain and shared tags for sweep synthesis."""
        all_nodes = self.store.list_nodes()
        obs = [n for n in all_nodes if n.type == "observation"]
        if domain:
            obs = [n for n in obs if n.domain.lower() == domain.lower()]

        by_domain: dict[str, list[str]] = {}
        for o in obs:
            d = o.domain or "general"
            by_domain.setdefault(d, []).append(o.id)

        clusters: list[SweepCluster] = []
        for d_name, ids in by_domain.items():
            if len(ids) >= 2:
                clusters.append(
                    SweepCluster(
                        theme=f"{d_name.capitalize()} Mechanism Cluster",
                        observation_ids=ids,
                        synthesis_notes=f"Group of {len(ids)} unlinked observations in domain {d_name}.",
                    )
                )
        return clusters

    def log_sweep(self, resurfaced: list[ResurfacedNode], author: Author | None = None) -> None:
        """Log resurface sweep execution event to event log."""
        auth = author or Author(kind=AuthorKind.HUMAN, courier="web-ui")
        self.store.event_log.append(
            kind="resurface_sweep_executed",
            subject_id=None,
            author=auth,
            payload={"count": len(resurfaced), "node_ids": [r.node.id for r in resurfaced]},
        )
